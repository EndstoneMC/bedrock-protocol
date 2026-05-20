"""Lower a `ResolvedFileDescriptor` into a `RenderedFile` the Jinja
templates print. All C++-specific decisions — type spelling, namespace
layout, serializer bodies — live here.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from ...descriptor import (
    CompilerError,
    CondWire,
    EnumDescriptor,
    EnumValueDescriptor,
    EnumWire,
    FieldDescriptor,
    MappingRef,
    MappingWire,
    NamedRef,
    OptionalRef,
    OptionalWire,
    Predicate,
    PrimitiveRef,
    RepeatedRef,
    RepeatedWire,
    ResolvedFileDescriptor,
    ScalarWire,
    StringWire,
    StructDescriptor,
    StructWire,
    SwitchWire,
    TypeAliasDescriptor,
    TypeRef,
    VariantRef,
    VersionSnapshot,
    Wire,
)
from .code_buffer import CodeBuffer
from .names import PRIMITIVE_TYPES, camel, requires_clause, snapshot_namespace
from .render import (
    RenderEntry,
    RenderEnum,
    RenderNamespace,
    RenderSerializer,
    RenderStruct,
    RenderTrait,
    RenderedFile,
)


class FileGenerator:
    """One `ResolvedFileDescriptor` → one `RenderedFile`."""

    def __init__(self, resolved: ResolvedFileDescriptor) -> None:
        self._resolved = resolved
        self._file = resolved.file
        self._file_set = resolved.file_set
        # Names every backend knows: types, primitive aliases, type aliases,
        # imported types. Anything else is either a builtin or unresolvable.
        self._known: frozenset[str] = frozenset(
            name
            for f in resolved.file_set.files.values()
            for name in (
                *(e.name for e in f.enums),
                *(s.name for s in f.structs),
                *(a.name for a in f.primitive_aliases),
                *(a.name for a in f.type_aliases),
            )
        )
        # `@builtin` types plus the stdlib UUID: emit no definition; route
        # through hand-written `Serializer` specializations.
        self._builtins = resolved.file_set.builtins | frozenset({"UUID"})
        # Serializer-walk state — set per call to _struct_serializer / etc.
        self._snapshot: int | None = None
        self._owner_qualified = ""
        self._nested_enums: frozenset[str] = frozenset()
        self._loop_depth = 0

    # --- top-level driver ----------------------------------------------------

    def render(self, latest_version: int) -> RenderedFile:
        file = self._file
        all_types: tuple[EnumDescriptor | StructDescriptor, ...] = (
            *file.enums, *file.structs,
        )
        by_name: dict[str, EnumDescriptor | StructDescriptor] = {
            t.name: t for t in all_types
        }

        primitive_aliases = [
            (a.name, PRIMITIVE_TYPES[a.primitive])
            for a in file.primitive_aliases
        ]
        type_aliases: list[tuple[str, str]] = []
        for a in file.type_aliases:
            for ref in a.target.referenced:
                if self._resolved.is_versioned(ref):
                    raise CompilerError(
                        f"{a.name}: a `type` alias cannot reference the "
                        f"versioned type {ref!r}"
                    )
            ctype = self._cpp_type(a.target, frozenset())
            assert ctype is not None
            type_aliases.append((a.name, ctype))

        unversioned: list[RenderEnum | RenderStruct] = []
        for name in self._resolved.declaration_order:
            if not self._resolved.is_versioned(name):
                unversioned.append(self._definition(by_name[name]))

        namespaces: list[RenderNamespace] = []
        for snap in self._resolved.snapshots:
            entries: list[RenderEntry] = []
            for name in self._resolved.declaration_order:
                if not self._resolved.is_versioned(name):
                    continue
                view = self._resolved.present_at(name, snap)
                if view is None:
                    continue
                if view.is_fresh:
                    narrowed = view.enum or view.struct
                    assert narrowed is not None
                    entries.append(RenderEntry(
                        alias=False,
                        definition=self._definition(narrowed),
                    ))
                else:
                    entries.append(RenderEntry(
                        alias=True,
                        name=name,
                        target=snapshot_namespace(view.concrete),
                    ))
            if entries:
                namespaces.append(RenderNamespace(snapshot_namespace(snap), entries))

        traits: list[RenderTrait] = []
        for name in self._resolved.declaration_order:
            if not self._resolved.is_versioned(name):
                continue
            fresh = self._resolved.fresh_snapshots(name)
            ranges = [
                (requires_clause(s.lo, _next_fresh_lo(fresh, i)), snapshot_namespace(s.lo))
                for i, s in enumerate(fresh)
            ]
            traits.append(RenderTrait(name, ranges))

        referenced = frozenset().union(
            *(s.referenced for s in file.structs),
            *(a.target.referenced for a in file.type_aliases),
        )
        dep_includes = [
            d.replace(".", "/") + ".hpp"
            for d in file.imports
            if self._import_has_content(d)
        ]
        latest_aliases = [
            name for name in self._resolved.declaration_order
            if self._resolved.is_versioned(name)
        ]

        return RenderedFile(
            package=file.package.replace(".", "::") if file.package else None,
            dep_includes=dep_includes,
            primitive_aliases=primitive_aliases,
            type_aliases=type_aliases,
            unversioned=unversioned,
            namespaces=namespaces,
            traits=traits,
            serializers=self._serializers(by_name),
            latest_aliases=latest_aliases,
            latest_version=latest_version,
            uses_uuid="UUID" in referenced,
            uses_nbt=bool(referenced & self._file_set.builtins),
        )

    def _import_has_content(self, dep: str) -> bool:
        other = self._file_set.files.get(dep)
        if other is None:
            return False
        return bool(other.enums or other.structs or other.primitive_aliases or other.type_aliases)

    # --- type definitions ----------------------------------------------------

    def _definition(
        self, t: EnumDescriptor | StructDescriptor
    ) -> RenderEnum | RenderStruct:
        if isinstance(t, EnumDescriptor):
            return self._enum_def(t)
        return self._struct_def(t)

    def _enum_def(self, e: EnumDescriptor) -> RenderEnum:
        return RenderEnum(e.name, [(camel(v.name), v.number) for v in e.values])

    def _struct_def(self, s: StructDescriptor) -> RenderStruct:
        nested = frozenset(e.name for e in s.nested_enums)
        rendered: list[tuple[str, str]] = []
        for f in s.fields:
            (era,) = f.eras
            ctype = self._cpp_type(era.type_ref, nested) if era.type_ref is not None else None
            if ctype is None:
                # Unresolvable field — degrade to a bare struct.
                return RenderStruct(s.name, [], [], [])
            rendered.append((ctype, f.name))
        constants: list[tuple[str, str, str]] = []
        if s.packet_id is not None:
            constants.append(("Id", "int", str(s.packet_id)))
        nested_defs = [self._enum_def(e) for e in s.nested_enums]
        return RenderStruct(s.name, nested_defs, constants, rendered)

    def _cpp_type(self, type_ref: TypeRef | None, nested: frozenset[str]) -> str | None:
        if type_ref is None:
            return None
        if isinstance(type_ref, PrimitiveRef):
            return PRIMITIVE_TYPES.get(type_ref.name)
        if isinstance(type_ref, NamedRef):
            name = type_ref.name
            if name in nested or name in self._known or name in self._builtins:
                return name
            return None
        if isinstance(type_ref, OptionalRef):
            inner = self._cpp_type(type_ref.inner, nested)
            return None if inner is None else f"std::optional<{inner}>"
        if isinstance(type_ref, RepeatedRef):
            inner = self._cpp_type(type_ref.inner, nested)
            if inner is None:
                return None
            if type_ref.count is None:
                return f"std::vector<{inner}>"
            return f"std::array<{inner}, {type_ref.count}>"
        if isinstance(type_ref, MappingRef):
            key = self._cpp_type(type_ref.key, nested)
            value = self._cpp_type(type_ref.value, nested)
            if key is None or value is None:
                return None
            return f"std::map<{key}, {value}>"
        if isinstance(type_ref, VariantRef):
            parts: list[str] = []
            for arm in type_ref.arms:
                if arm is None:
                    parts.append("std::monostate")
                    continue
                arm_type = self._cpp_type(arm, nested)
                if arm_type is None:
                    return None
                parts.append(arm_type)
            return f"std::variant<{', '.join(parts)}>"
        return None

    # --- serializers ---------------------------------------------------------

    def _serializers(
        self, by_name: dict[str, EnumDescriptor | StructDescriptor]
    ) -> list[RenderSerializer]:
        string_coded = self._string_coded_enums()
        out: list[RenderSerializer] = []
        for name in self._resolved.declaration_order:
            t = by_name[name]
            if self._resolved.is_versioned(name):
                fresh = self._resolved.fresh_snapshots(name)
            else:
                fresh = ()
            if isinstance(t, EnumDescriptor):
                if name not in string_coded:
                    continue
                if not fresh:
                    out.append(self._enum_serializer(t, None))
                else:
                    out.extend(self._enum_serializer_from_snapshot(s) for s in fresh)
            else:
                if not fresh:
                    rendered = self._struct_serializer(t, None)
                    if rendered is not None:
                        out.append(rendered)
                else:
                    for s in fresh:
                        assert s.struct is not None
                        rendered = self._struct_serializer(t, s.struct, snapshot=s.lo)
                        if rendered is not None:
                            out.append(rendered)
        for a in self._file.type_aliases:
            if isinstance(a.target, VariantRef):
                out.append(self._variant_alias_serializer(a))
        return out

    def _enum_serializer_from_snapshot(self, snap: VersionSnapshot) -> RenderSerializer:
        assert snap.enum is not None
        return self._enum_serializer(snap.enum, snap.lo)

    def _string_coded_enums(self) -> frozenset[str]:
        """Module-scope enums some field encodes by name — they need a
        `Serializer` specialization. Integer-coded ones inline a cast."""
        out: set[str] = set()
        for struct in self._file.structs:
            for f in struct.fields:
                for era in f.eras:
                    w = era.wire
                    while isinstance(w, (OptionalWire, CondWire)):
                        w = w.inner
                    if isinstance(w, EnumWire) and w.scalar is None:
                        out.add(w.name)
        return frozenset(out)

    def _struct_serializer(
        self,
        struct: StructDescriptor,
        view: StructDescriptor | None,
        snapshot: int | None = None,
    ) -> RenderSerializer | None:
        if view is None:
            fields = struct.fields
            qualified = struct.name
        else:
            assert snapshot is not None
            fields = view.fields
            qualified = f"{snapshot_namespace(snapshot)}::{struct.name}"
        wired: list[tuple[FieldDescriptor, Wire]] = []
        for f in fields:
            w = f.wire_single
            if w is None:
                return None
            wired.append((f, w))
        self._snapshot, self._owner_qualified = snapshot, qualified
        self._nested_enums = frozenset(e.name for e in struct.nested_enums)
        groups = _field_groups(wired)

        serialize = CodeBuffer()
        for guard, group in groups:
            if guard is None:
                ((f, w),) = group
                self._emit_write(serialize, f.type_ref_single, w, f"value.{f.name}")
                continue
            with serialize.block(f"if ({self._render_predicate(guard, 'value')})"):
                for f, w in group:
                    assert isinstance(w, CondWire)
                    self._emit_write(serialize, f.type_ref_single, w.inner, f"value.{f.name}")

        deserialize = CodeBuffer()
        deserialize(f"{qualified} out;")
        for guard, group in groups:
            if guard is None:
                ((f, w),) = group
                with deserialize.block():
                    self._emit_read(deserialize, f.type_ref_single, w, f"out.{f.name}")
                continue
            with deserialize.block(f"if ({self._render_predicate(guard, 'out')})"):
                for f, w in group:
                    assert isinstance(w, CondWire)
                    with deserialize.block():
                        self._emit_read(deserialize, f.type_ref_single, w.inner, f"out.{f.name}")
        deserialize("return out;")
        return RenderSerializer(
            qualified, f"const {qualified} &value", serialize.lines, deserialize.lines
        )

    def _variant_alias_serializer(self, a: TypeAliasDescriptor) -> RenderSerializer:
        self._snapshot, self._owner_qualified, self._nested_enums = (
            None, a.name, frozenset()
        )
        serialize = CodeBuffer()
        self._emit_write(serialize, a.target, a.wire, "value")
        deserialize = CodeBuffer()
        deserialize(f"{a.name} out;")
        self._emit_read(deserialize, a.target, a.wire, "out")
        deserialize("return out;")
        return RenderSerializer(
            a.name, f"const {a.name} &value", serialize.lines, deserialize.lines
        )

    def _enum_serializer(
        self, enum: EnumDescriptor, snapshot: int | None
    ) -> RenderSerializer:
        if snapshot is None:
            values, qualified = enum.values, enum.name
        else:
            values = enum.values
            qualified = f"{snapshot_namespace(snapshot)}::{enum.name}"
        serialize = CodeBuffer()
        serialize(f"using E = {qualified};")
        for v in values:
            serialize(
                f"if (value == E::{camel(v.name)}) {{ "
                f'stream.write(std::string_view{{"{v.wire_name}"}}); return; }}'
            )
        deserialize = CodeBuffer()
        deserialize(f"using E = {qualified};")
        deserialize("auto v = stream.read<std::string>();")
        deserialize("if (!v) return make_unexpected(v.error());")
        for v in values:
            deserialize(f'if (*v == "{v.wire_name}") return E::{camel(v.name)};')
        deserialize(
            "return make_unexpected("
            "std::make_error_code(std::errc::illegal_byte_sequence));"
        )
        return RenderSerializer(
            qualified, f"{qualified} value", serialize.lines, deserialize.lines
        )

    # --- serialize body emission --------------------------------------------

    def _emit_write(
        self, code: CodeBuffer, type_ref: TypeRef | None, wire: Wire, expr: str
    ) -> None:
        if isinstance(wire, ScalarWire):
            code(_scalar_write(wire, expr))
        elif isinstance(wire, StringWire):
            code(f"stream.write({expr});")
        elif isinstance(wire, StructWire):
            code(f"Serializer<{self._type_at(wire.name)}>::serialize(stream, {expr});")
        elif isinstance(wire, EnumWire):
            if wire.scalar is None:
                code(f"Serializer<{self._type_at(wire.name)}>::serialize(stream, {expr});")
            else:
                code(_scalar_write(wire.scalar, expr))
        elif isinstance(wire, OptionalWire):
            if wire.discriminator:
                code(
                    f"stream.writeVarInt<std::uint32_t>"
                    f"({expr}.has_value() ? {wire.present_tag}u : {1 - wire.present_tag}u);"
                )
            else:
                code(f"stream.write<bool>({expr}.has_value());")
            assert isinstance(type_ref, OptionalRef)
            with code.block(f"if ({expr}.has_value())"):
                self._emit_write(code, type_ref.inner, wire.inner, f"*{expr}")
        elif isinstance(wire, RepeatedWire):
            assert isinstance(type_ref, RepeatedRef)
            depth = self._loop_depth
            self._loop_depth += 1
            if wire.prefix is not None:
                code(_scalar_write(wire.prefix, f"{expr}.size()"))
            with code.block(f"for (const auto &e{depth} : {expr})"):
                self._emit_write(code, type_ref.inner, wire.inner, f"e{depth}")
            self._loop_depth -= 1
        elif isinstance(wire, MappingWire):
            assert isinstance(type_ref, MappingRef)
            depth = self._loop_depth
            self._loop_depth += 1
            code(_scalar_write(wire.prefix, f"{expr}.size()"))
            with code.block(f"for (const auto &[k{depth}, v{depth}] : {expr})"):
                self._emit_write(code, type_ref.key, wire.key, f"k{depth}")
                self._emit_write(code, type_ref.value, wire.value, f"v{depth}")
            self._loop_depth -= 1
        elif isinstance(wire, SwitchWire):
            assert isinstance(type_ref, VariantRef)
            code(f"stream.writeVarInt<std::uint32_t>(({expr}).index());")
            with code.block(f"switch (({expr}).index())"):
                for index, arm in enumerate(wire.arms):
                    with code.block(f"case {index}:"):
                        if arm is not None:
                            self._emit_write(
                                code, type_ref.arms[index], arm,
                                f"std::get<{index}>({expr})",
                            )
                        code("break;")

    def _emit_read(
        self, code: CodeBuffer, type_ref: TypeRef | None, wire: Wire, target: str
    ) -> None:
        if isinstance(wire, ScalarWire):
            _scalar_read(code, wire)
            cast = self._cpp_type(type_ref, self._nested_enums)
            code(f"{target} = static_cast<{cast}>(*v);")
        elif isinstance(wire, StringWire):
            code("auto v = stream.read<std::string>();")
            code("if (!v) return make_unexpected(v.error());")
            code(f"{target} = *v;")
        elif isinstance(wire, StructWire):
            code(f"auto v = Serializer<{self._type_at(wire.name)}>::deserialize(stream);")
            code("if (!v) return make_unexpected(v.error());")
            code(f"{target} = *v;")
        elif isinstance(wire, EnumWire):
            if wire.scalar is None:
                code(f"auto v = Serializer<{self._type_at(wire.name)}>::deserialize(stream);")
                code("if (!v) return make_unexpected(v.error());")
                code(f"{target} = *v;")
            else:
                _scalar_read(code, wire.scalar)
                code(f"{target} = static_cast<{self._type_at(wire.name)}>(*v);")
        elif isinstance(wire, OptionalWire):
            holder = "tag" if wire.discriminator else "present"
            verb = "readVarInt<std::uint32_t>" if wire.discriminator else "read<bool>"
            guard = f"*tag == {wire.present_tag}" if wire.discriminator else "*present"
            code(f"auto {holder} = stream.{verb}();")
            code(f"if (!{holder}) return make_unexpected({holder}.error());")
            assert isinstance(type_ref, OptionalRef)
            with code.block(f"if ({guard})"):
                self._emit_read(code, type_ref.inner, wire.inner, target)
        elif isinstance(wire, RepeatedWire):
            assert isinstance(type_ref, RepeatedRef)
            depth = self._loop_depth
            self._loop_depth += 1
            if wire.prefix is not None:
                u = PRIMITIVE_TYPES[wire.prefix.primitive]
                verb = f"readVarInt<{u}>" if wire.prefix.varint else f"read<{u}>"
                code(f"auto len{depth} = stream.{verb}();")
                code(f"if (!len{depth}) return make_unexpected(len{depth}.error());")
                code(f"{target}.clear();")
                head = (
                    f"for (auto rep{depth} = *len{depth}; "
                    f"rep{depth} > 0; --rep{depth})"
                )
                with code.block(head):
                    code(f"{target}.emplace_back();")
                    self._emit_read(code, type_ref.inner, wire.inner, f"{target}.back()")
            else:
                head = (
                    f"for (std::size_t i{depth} = 0; "
                    f"i{depth} < {wire.count}; ++i{depth})"
                )
                with code.block(head):
                    self._emit_read(code, type_ref.inner, wire.inner, f"{target}[i{depth}]")
            self._loop_depth -= 1
        elif isinstance(wire, MappingWire):
            assert isinstance(type_ref, MappingRef)
            depth = self._loop_depth
            self._loop_depth += 1
            u = PRIMITIVE_TYPES[wire.prefix.primitive]
            verb = f"readVarInt<{u}>" if wire.prefix.varint else f"read<{u}>"
            code(f"auto len{depth} = stream.{verb}();")
            code(f"if (!len{depth}) return make_unexpected(len{depth}.error());")
            code(f"{target}.clear();")
            holder = f"std::remove_reference_t<decltype({target})>"
            head = (
                f"for (auto rep{depth} = *len{depth}; "
                f"rep{depth} > 0; --rep{depth})"
            )
            with code.block(head):
                code(f"{holder}::key_type k{depth}{{}};")
                with code.block():
                    self._emit_read(code, type_ref.key, wire.key, f"k{depth}")
                code(f"{holder}::mapped_type v{depth}{{}};")
                with code.block():
                    self._emit_read(code, type_ref.value, wire.value, f"v{depth}")
                code(f"{target}.emplace(k{depth}, v{depth});")
            self._loop_depth -= 1
        elif isinstance(wire, SwitchWire):
            assert isinstance(type_ref, VariantRef)
            depth = self._loop_depth
            self._loop_depth += 1
            vartype = self._cpp_type(type_ref, self._nested_enums)
            assert vartype is not None
            code(f"auto tag{depth} = stream.readVarInt<std::uint32_t>();")
            code(f"if (!tag{depth}) return make_unexpected(tag{depth}.error());")
            code(f"{vartype} var{depth}{{}};")
            with code.block(f"switch (*tag{depth})"):
                for index, arm in enumerate(wire.arms):
                    with code.block(f"case {index}:"):
                        code(
                            f"std::variant_alternative_t<{index}, {vartype}> "
                            f"arm{depth}{{}};"
                        )
                        if arm is not None:
                            with code.block():
                                self._emit_read(
                                    code, type_ref.arms[index], arm, f"arm{depth}"
                                )
                        code(f"var{depth}.emplace<{index}>(arm{depth});")
                        code("break;")
                with code.block("default:"):
                    code(
                        "return make_unexpected(std::make_error_code("
                        "std::errc::illegal_byte_sequence));"
                    )
            code(f"{target} = var{depth};")
            self._loop_depth -= 1

    # --- helpers -------------------------------------------------------------

    def _render_predicate(self, pred: Predicate, base: str) -> str:
        if pred.kind == "field":
            return f"{base}.{pred.text}"
        if pred.kind == "int":
            return pred.text
        if pred.kind == "enum":
            enum, member = pred.text.rsplit(".", 1)
            return f"{self._type_at(enum)}::{camel(member)}"
        if pred.kind == "not":
            return f"!({self._render_predicate(pred.operands[0], base)})"
        op = {"and": "&&", "or": "||"}.get(pred.kind, pred.kind)
        return f" {op} ".join(
            f"({self._render_predicate(o, base)})" for o in pred.operands
        )

    def _type_at(self, name: str) -> str:
        """Qualified spelling of `name` from inside a serializer at `self._snapshot`."""
        if name in self._nested_enums:
            return f"{self._owner_qualified}::{name}"
        if self._resolved.is_versioned(name):
            assert self._snapshot is not None
            view = self._resolved.present_at(name, self._snapshot)
            assert view is not None
            return f"{snapshot_namespace(view.concrete)}::{name}"
        return name


# --- helpers --------------------------------------------------------------------


def _next_fresh_lo(fresh: Sequence[VersionSnapshot], i: int) -> int | None:
    return fresh[i + 1].lo if i + 1 < len(fresh) else None


def _field_groups(
    wired: list[tuple[FieldDescriptor, Wire]],
) -> list[tuple[Predicate | None, list[tuple[FieldDescriptor, Wire]]]]:
    """Partition a struct's fields into emission groups. Fields from one
    `with field(when=...)` block (carrying the same `CondWire.group`) form
    one group emitted under a shared `if`; everything else stands alone."""
    groups: list[tuple[Predicate | None, list[tuple[FieldDescriptor, Wire]]]] = []
    open_group: int | None = None
    for f, w in wired:
        if (
            isinstance(w, CondWire)
            and w.group is not None
            and w.group == open_group
        ):
            groups[-1][1].append((f, w))
            continue
        if isinstance(w, CondWire):
            groups.append((w.predicate, [(f, w)]))
            open_group = w.group
        else:
            groups.append((None, [(f, w)]))
            open_group = None
    return groups


def _scalar_write(scalar: ScalarWire, expr: str) -> str:
    u = PRIMITIVE_TYPES[scalar.primitive]
    if scalar.varint:
        return f"stream.writeVarInt<{u}>({expr});"
    if scalar.big_endian:
        return f"stream.write<{u}, std::endian::big>({expr});"
    return f"stream.write<{u}>({expr});"


def _scalar_read(code: CodeBuffer, scalar: ScalarWire) -> None:
    u = PRIMITIVE_TYPES[scalar.primitive]
    if scalar.varint:
        code(f"auto v = stream.readVarInt<{u}>();")
    elif scalar.big_endian:
        code(f"auto v = stream.read<{u}, std::endian::big>();")
    else:
        code(f"auto v = stream.read<{u}>();")
    code("if (!v) return make_unexpected(v.error());")
