"""Lower a `ResolvedFile` into a `RenderedFile` the Jinja templates print.
All C++-specific decisions — type spelling, namespace layout, serializer
bodies — live here.
"""

from __future__ import annotations

from typing import Sequence

from ...descriptor import (
    VARINT_PRIMITIVES,
    CompilerError,
    CondType,
    Enum,
    EnumType,
    Field,
    FieldType,
    MappingType,
    OptionalType,
    Predicate,
    PrimitiveType,
    RepeatedType,
    ResolvedFile,
    Struct,
    StructType,
    TypeAlias,
    VariantType,
    VersionSnapshot,
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
    """One `ResolvedFile` → one `RenderedFile`."""

    def __init__(self, resolved: ResolvedFile) -> None:
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
        all_types: tuple[Enum | Struct, ...] = (
            *file.enums, *file.structs,
        )
        by_name: dict[str, Enum | Struct] = {
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
        self, t: Enum | Struct
    ) -> RenderEnum | RenderStruct:
        if isinstance(t, Enum):
            return self._enum_def(t)
        return self._struct_def(t)

    def _enum_def(self, e: Enum) -> RenderEnum:
        return RenderEnum(e.name, [(camel(v.name), v.number) for v in e.values])

    def _struct_def(self, s: Struct) -> RenderStruct:
        nested = frozenset(e.name for e in s.nested_enums)
        rendered: list[tuple[str, str]] = []
        for f in s.fields:
            (version,) = f.versions
            ctype = self._cpp_type(version.type, nested) if version.type is not None else None
            if ctype is None:
                # Unresolvable field — degrade to a bare struct.
                return RenderStruct(s.name, [], [], [])
            rendered.append((ctype, f.name))
        constants: list[tuple[str, str, str]] = []
        if s.packet_id is not None:
            constants.append(("Id", "int", str(s.packet_id)))
        nested_defs = [self._enum_def(e) for e in s.nested_enums]
        return RenderStruct(s.name, nested_defs, constants, rendered)

    def _cpp_type(self, t: FieldType | None, nested: frozenset[str]) -> str | None:
        if t is None:
            return None
        if isinstance(t, PrimitiveType):
            if t.alias is not None:
                return t.alias
            return PRIMITIVE_TYPES.get(t.name)
        if isinstance(t, (StructType, EnumType)):
            name = t.name
            if name in nested or name in self._known or name in self._builtins:
                return name
            return None
        if isinstance(t, OptionalType):
            inner = self._cpp_type(t.inner, nested)
            return None if inner is None else f"std::optional<{inner}>"
        if isinstance(t, RepeatedType):
            inner = self._cpp_type(t.inner, nested)
            if inner is None:
                return None
            if t.count is None:
                return f"std::vector<{inner}>"
            return f"std::array<{inner}, {t.count}>"
        if isinstance(t, MappingType):
            key = self._cpp_type(t.key, nested)
            value = self._cpp_type(t.value, nested)
            if key is None or value is None:
                return None
            return f"std::map<{key}, {value}>"
        if isinstance(t, VariantType):
            parts: list[str] = []
            for arm in t.arms:
                if arm is None:
                    parts.append("std::monostate")
                    continue
                arm_type = self._cpp_type(arm, nested)
                if arm_type is None:
                    return None
                parts.append(arm_type)
            return f"std::variant<{', '.join(parts)}>"
        if isinstance(t, CondType):
            return self._cpp_type(t.inner, nested)
        return None

    # --- serializers ---------------------------------------------------------

    def _serializers(
        self, by_name: dict[str, Enum | Struct]
    ) -> list[RenderSerializer]:
        string_coded = self._string_coded_enums()
        out: list[RenderSerializer] = []
        for name in self._resolved.declaration_order:
            t = by_name[name]
            if self._resolved.is_versioned(name):
                fresh = self._resolved.fresh_snapshots(name)
            else:
                fresh = ()
            if isinstance(t, Enum):
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
            if isinstance(a.target, VariantType):
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
                for version in f.versions:
                    t = version.type
                    while isinstance(t, (OptionalType, CondType)):
                        t = t.inner
                    if isinstance(t, EnumType) and t.scalar is None:
                        out.add(t.name)
        return frozenset(out)

    def _struct_serializer(
        self,
        struct: Struct,
        view: Struct | None,
        snapshot: int | None = None,
    ) -> RenderSerializer | None:
        if view is None:
            fields = struct.fields
            qualified = struct.name
        else:
            assert snapshot is not None
            fields = view.fields
            qualified = f"{snapshot_namespace(snapshot)}::{struct.name}"
        typed: list[tuple[Field, FieldType]] = []
        for f in fields:
            t = f.type_single
            if t is None:
                return None
            typed.append((f, t))
        self._snapshot, self._owner_qualified = snapshot, qualified
        self._nested_enums = frozenset(e.name for e in struct.nested_enums)
        groups = _field_groups(typed)

        serialize = CodeBuffer()
        for guard, group in groups:
            if guard is None:
                ((f, t),) = group
                self._emit_write(serialize, t, f"value.{f.name}")
                continue
            with serialize.block(f"if ({self._render_predicate(guard, 'value')})"):
                for f, t in group:
                    assert isinstance(t, CondType)
                    self._emit_write(serialize, t.inner, f"value.{f.name}")

        deserialize = CodeBuffer()
        deserialize(f"{qualified} out;")
        for guard, group in groups:
            if guard is None:
                ((f, t),) = group
                with deserialize.block():
                    self._emit_read(deserialize, t, f"out.{f.name}")
                continue
            with deserialize.block(f"if ({self._render_predicate(guard, 'out')})"):
                for f, t in group:
                    assert isinstance(t, CondType)
                    with deserialize.block():
                        self._emit_read(deserialize, t.inner, f"out.{f.name}")
        deserialize("return out;")
        return RenderSerializer(
            qualified, f"const {qualified} &value", serialize.lines, deserialize.lines
        )

    def _variant_alias_serializer(self, a: TypeAlias) -> RenderSerializer:
        self._snapshot, self._owner_qualified, self._nested_enums = (
            None, a.name, frozenset()
        )
        serialize = CodeBuffer()
        self._emit_write(serialize, a.target, "value")
        deserialize = CodeBuffer()
        deserialize(f"{a.name} out;")
        self._emit_read(deserialize, a.target, "out")
        deserialize("return out;")
        return RenderSerializer(
            a.name, f"const {a.name} &value", serialize.lines, deserialize.lines
        )

    def _enum_serializer(
        self, enum: Enum, snapshot: int | None
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
        self, code: CodeBuffer, t: FieldType, expr: str
    ) -> None:
        if isinstance(t, PrimitiveType):
            code(_primitive_write(t, expr))
        elif isinstance(t, StructType):
            code(f"Serializer<{self._type_at(t.name)}>::serialize(stream, {expr});")
        elif isinstance(t, EnumType):
            if t.scalar is None:
                code(f"Serializer<{self._type_at(t.name)}>::serialize(stream, {expr});")
            else:
                code(_primitive_write(t.scalar, expr))
        elif isinstance(t, OptionalType):
            if t.discriminator:
                code(
                    f"stream.writeVarInt<std::uint32_t>"
                    f"({expr}.has_value() ? {t.present_tag}u : {1 - t.present_tag}u);"
                )
            else:
                code(f"stream.write<bool>({expr}.has_value());")
            with code.block(f"if ({expr}.has_value())"):
                self._emit_write(code, t.inner, f"*{expr}")
        elif isinstance(t, RepeatedType):
            depth = self._loop_depth
            self._loop_depth += 1
            if t.prefix is not None:
                code(_primitive_write(t.prefix, f"{expr}.size()"))
            with code.block(f"for (const auto &e{depth} : {expr})"):
                self._emit_write(code, t.inner, f"e{depth}")
            self._loop_depth -= 1
        elif isinstance(t, MappingType):
            depth = self._loop_depth
            self._loop_depth += 1
            code(_primitive_write(t.prefix, f"{expr}.size()"))
            with code.block(f"for (const auto &[k{depth}, v{depth}] : {expr})"):
                self._emit_write(code, t.key, f"k{depth}")
                self._emit_write(code, t.value, f"v{depth}")
            self._loop_depth -= 1
        elif isinstance(t, VariantType):
            code(f"stream.writeVarInt<std::uint32_t>(({expr}).index());")
            with code.block(f"switch (({expr}).index())"):
                for index, arm in enumerate(t.arms):
                    with code.block(f"case {index}:"):
                        if arm is not None:
                            self._emit_write(
                                code, arm, f"std::get<{index}>({expr})"
                            )
                        code("break;")
        elif isinstance(t, CondType):
            # Reached only at the top of a struct walk; the caller has
            # already opened the guarded `if` block.
            self._emit_write(code, t.inner, expr)

    def _emit_read(
        self, code: CodeBuffer, t: FieldType, target: str
    ) -> None:
        if isinstance(t, PrimitiveType):
            _primitive_read(code, t)
            if t.name in ("str", "bytes") and t.alias is None:
                code(f"{target} = *v;")
            else:
                cast = self._cpp_type(t, self._nested_enums)
                code(f"{target} = static_cast<{cast}>(*v);")
        elif isinstance(t, StructType):
            code(f"auto v = Serializer<{self._type_at(t.name)}>::deserialize(stream);")
            code("if (!v) return make_unexpected(v.error());")
            code(f"{target} = *v;")
        elif isinstance(t, EnumType):
            if t.scalar is None:
                code(f"auto v = Serializer<{self._type_at(t.name)}>::deserialize(stream);")
                code("if (!v) return make_unexpected(v.error());")
                code(f"{target} = *v;")
            else:
                _primitive_read(code, t.scalar)
                code(f"{target} = static_cast<{self._type_at(t.name)}>(*v);")
        elif isinstance(t, OptionalType):
            holder = "tag" if t.discriminator else "present"
            verb = "readVarInt<std::uint32_t>" if t.discriminator else "read<bool>"
            guard = f"*tag == {t.present_tag}" if t.discriminator else "*present"
            code(f"auto {holder} = stream.{verb}();")
            code(f"if (!{holder}) return make_unexpected({holder}.error());")
            with code.block(f"if ({guard})"):
                self._emit_read(code, t.inner, target)
        elif isinstance(t, RepeatedType):
            depth = self._loop_depth
            self._loop_depth += 1
            if t.prefix is not None:
                u = PRIMITIVE_TYPES[t.prefix.name]
                verb = (
                    f"readVarInt<{u}>"
                    if t.prefix.name in VARINT_PRIMITIVES
                    else f"read<{u}>"
                )
                code(f"auto len{depth} = stream.{verb}();")
                code(f"if (!len{depth}) return make_unexpected(len{depth}.error());")
                code(f"{target}.clear();")
                head = (
                    f"for (auto rep{depth} = *len{depth}; "
                    f"rep{depth} > 0; --rep{depth})"
                )
                with code.block(head):
                    code(f"{target}.emplace_back();")
                    self._emit_read(code, t.inner, f"{target}.back()")
            else:
                head = (
                    f"for (std::size_t i{depth} = 0; "
                    f"i{depth} < {t.count}; ++i{depth})"
                )
                with code.block(head):
                    self._emit_read(code, t.inner, f"{target}[i{depth}]")
            self._loop_depth -= 1
        elif isinstance(t, MappingType):
            depth = self._loop_depth
            self._loop_depth += 1
            u = PRIMITIVE_TYPES[t.prefix.name]
            verb = (
                f"readVarInt<{u}>"
                if t.prefix.name in VARINT_PRIMITIVES
                else f"read<{u}>"
            )
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
                    self._emit_read(code, t.key, f"k{depth}")
                code(f"{holder}::mapped_type v{depth}{{}};")
                with code.block():
                    self._emit_read(code, t.value, f"v{depth}")
                code(f"{target}.emplace(k{depth}, v{depth});")
            self._loop_depth -= 1
        elif isinstance(t, VariantType):
            depth = self._loop_depth
            self._loop_depth += 1
            vartype = self._cpp_type(t, self._nested_enums)
            assert vartype is not None
            code(f"auto tag{depth} = stream.readVarInt<std::uint32_t>();")
            code(f"if (!tag{depth}) return make_unexpected(tag{depth}.error());")
            code(f"{vartype} var{depth}{{}};")
            with code.block(f"switch (*tag{depth})"):
                for index, arm in enumerate(t.arms):
                    with code.block(f"case {index}:"):
                        code(
                            f"std::variant_alternative_t<{index}, {vartype}> "
                            f"arm{depth}{{}};"
                        )
                        if arm is not None:
                            with code.block():
                                self._emit_read(code, arm, f"arm{depth}")
                        code(f"var{depth}.emplace<{index}>(arm{depth});")
                        code("break;")
                with code.block("default:"):
                    code(
                        "return make_unexpected(std::make_error_code("
                        "std::errc::illegal_byte_sequence));"
                    )
            code(f"{target} = var{depth};")
            self._loop_depth -= 1
        elif isinstance(t, CondType):
            self._emit_read(code, t.inner, target)

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
    typed: list[tuple[Field, FieldType]],
) -> list[tuple[Predicate | None, list[tuple[Field, FieldType]]]]:
    """Partition a struct's fields into emission groups. Fields from one
    `with field(when=...)` block (sharing a `CondType.group`) form one
    group emitted under a shared `if`; everything else stands alone."""
    groups: list[tuple[Predicate | None, list[tuple[Field, FieldType]]]] = []
    open_group: int | None = None
    for f, t in typed:
        if (
            isinstance(t, CondType)
            and t.group is not None
            and t.group == open_group
        ):
            groups[-1][1].append((f, t))
            continue
        if isinstance(t, CondType):
            groups.append((t.predicate, [(f, t)]))
            open_group = t.group
        else:
            groups.append((None, [(f, t)]))
            open_group = None
    return groups


def _primitive_write(p: PrimitiveType, expr: str) -> str:
    if p.name in ("str", "bytes"):
        return f"stream.write({expr});"
    u = PRIMITIVE_TYPES[p.name]
    if p.name in VARINT_PRIMITIVES:
        return f"stream.writeVarInt<{u}>({expr});"
    if p.big_endian:
        return f"stream.write<{u}, std::endian::big>({expr});"
    return f"stream.write<{u}>({expr});"


def _primitive_read(code: CodeBuffer, p: PrimitiveType) -> None:
    if p.name in ("str", "bytes"):
        code("auto v = stream.read<std::string>();")
    else:
        u = PRIMITIVE_TYPES[p.name]
        if p.name in VARINT_PRIMITIVES:
            code(f"auto v = stream.readVarInt<{u}>();")
        elif p.big_endian:
            code(f"auto v = stream.read<{u}, std::endian::big>();")
        else:
            code(f"auto v = stream.read<{u}>();")
    code("if (!v) return make_unexpected(v.error());")
