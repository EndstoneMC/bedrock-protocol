"""C++ backend: lower the `schema` IR plus a `VersionPlan` into a render model
the Jinja templates print verbatim. All target-language decisions -- type
spelling, namespace layout, serializer bodies -- are made here, so the
templates carry no logic. A second language would be a sibling of this module.
"""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import inflection

from .schema import (
    CompilerError,
    Cond,
    Enum,
    EnumMember,
    EnumRef,
    Field,
    Map,
    Mapping,
    Module,
    Named,
    Opt,
    Optional,
    Pred,
    PredAnd,
    PredCompare,
    PredEnum,
    PredField,
    PredInt,
    PredNot,
    PredOr,
    Primitive,
    PrimitiveAlias,
    Repeat,
    Repeated,
    Scalar,
    Schema,
    Str,
    Struct,
    StructRef,
    Switch,
    TypeAlias,
    TypeRef,
    Variant,
    Wire,
)
from .versioning import VersionPlan

#: DSL primitive -> C++ type. Varint vs fixed-width is carried by `Scalar`.
PRIMITIVE_TYPES: dict[str, str] = {
    "str": "std::string",
    "bytes": "std::string",
    "int": "int",
    "bool": "bool",
    "float": "float",
    "double": "double",
    "varint32": "std::int32_t",
    "varint64": "std::int64_t",
    "uvarint32": "std::uint32_t",
    "uvarint64": "std::uint64_t",
    "int8": "std::int8_t",
    "int16": "std::int16_t",
    "int32": "std::int32_t",
    "int64": "std::int64_t",
    "uint8": "std::uint8_t",
    "uint16": "std::uint16_t",
    "uint32": "std::uint32_t",
    "uint64": "std::uint64_t",
}


# --- render model: a header expressed as data --------------------------------


@dataclass
class RenderEnum:
    name: str
    members: list[tuple[str, int]]
    kind: str = "enum"


@dataclass
class RenderStruct:
    name: str
    nested_enums: list[RenderEnum]
    constants: list[tuple[str, str, str]]
    fields: list[tuple[str, str]]
    kind: str = "struct"


@dataclass
class RenderEntry:
    """One member of a snapshot namespace: a fresh definition or a `using`
    alias back to an earlier snapshot."""

    alias: bool
    name: str = ""
    target: str = ""
    definition: RenderEnum | RenderStruct | None = None


@dataclass
class RenderNamespace:
    name: str
    entries: list[RenderEntry]


@dataclass
class RenderTrait:
    name: str
    ranges: list[tuple[str, str]]  # (requires-clause, namespace)


@dataclass
class RenderSerializer:
    qualified: str
    param: str
    serialize: list[str]
    deserialize: list[str]


@dataclass
class RenderModule:
    package: str | None
    dep_includes: list[str]
    primitive_aliases: list[tuple[str, str]]  # `enum X : ctype {}` lines
    type_aliases: list[tuple[str, str]]       # `using X = ctype` lines (any non-primitive)
    unversioned: list[RenderEnum | RenderStruct]
    namespaces: list[RenderNamespace]
    traits: list[RenderTrait]
    serializers: list[RenderSerializer]
    latest_aliases: list[str]
    latest_version: int
    uses_uuid: bool
    uses_nbt: bool


class _Code:
    """An indentation-tracking line buffer for C++ method bodies. Bodies open
    two levels deep (inside `struct` then method); `block` nests further."""

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._depth = 2

    def __call__(self, text: str = "") -> None:
        self._lines.append("    " * self._depth + text if text else "")

    @contextmanager
    def block(self, head: str = "") -> Iterator[None]:
        self(f"{head} {{" if head else "{")
        self._depth += 1
        try:
            yield
        finally:
            self._depth -= 1
        self("}")

    @property
    def lines(self) -> list[str]:
        return self._lines


class CppBackend:
    def __init__(self, module: Module, schema: Schema, plan: VersionPlan):
        self._module = module
        self._schema = schema
        self._plan = plan
        self._known = frozenset(
            name
            for m in schema.modules.values()
            for name in (
                *(t.name for t in m.types),
                *(a.name for a in m.primitive_aliases),
                *(a.name for a in m.type_aliases),
            )
        )
        # `@builtin` types (NBT tags), plus the stdlib `uuid.UUID`. The compiler
        # emits no definition for these -- it resolves them by name and routes
        # them through a hand-written `Serializer` in an `<bedrock/*.hpp>`.
        self._builtins = schema.builtins | frozenset({"UUID"})
        # Per-serializer context, set by `_struct_serializer` / `_enum_serializer`.
        self._snap: int | None = None
        self._owner = ""
        self._nested: frozenset[str] = frozenset()
        # Nesting depth of the repeated field being emitted, for unique loop
        # variable names. Balanced by `_write` / `_read`, so it returns to 0.
        self._rep = 0

    def render(self, latest_version: int) -> RenderModule:
        self._guard_cross_module()
        module, plan = self._module, self._plan
        by_name = {t.name: t for t in module.types}

        primitive_aliases = [
            (a.name, PRIMITIVE_TYPES[a.primitive]) for a in module.primitive_aliases
        ]
        # A type alias lowers to a flat `using X = ...`; a versioned name
        # inside it has no single spelling there, so reject one.
        for a in module.type_aliases:
            for ref in a.target.referenced:
                if plan.is_versioned(ref):
                    raise CompilerError(
                        f"{a.name}: a `type` alias cannot reference the "
                        f"versioned type {ref!r}"
                    )
        type_aliases: list[tuple[str, str]] = []
        for a in module.type_aliases:
            ctype = self._cpp_type(a.target, frozenset())
            assert ctype is not None  # frontend would have rejected an unresolvable target
            type_aliases.append((a.name, ctype))

        unversioned: list[RenderEnum | RenderStruct] = []
        for name in plan.order:
            if not plan.is_versioned(name):
                unversioned.append(self._definition(by_name[name]))

        namespaces: list[RenderNamespace] = []
        for snapshot in plan.snapshots:
            entries: list[RenderEntry] = []
            for name in plan.order:
                if not plan.is_versioned(name) or not plan.present(name, snapshot):
                    continue
                if plan.fresh(name, snapshot):
                    definition = self._definition(
                        by_name[name], plan.visible(name, snapshot)
                    )
                    entries.append(RenderEntry(alias=False, definition=definition))
                else:
                    entries.append(RenderEntry(
                        alias=True,
                        name=name,
                        target=self._ns(plan.concrete(name, snapshot)),
                    ))
            if entries:  # a snapshot before every type's `since` is empty
                namespaces.append(RenderNamespace(self._ns(snapshot), entries))

        traits: list[RenderTrait] = []
        for name in plan.order:
            if plan.is_versioned(name):
                ranges = [
                    (self._clause(lo, hi), self._ns(lo))
                    for lo, hi in plan.ranges(name)
                ]
                traits.append(RenderTrait(name, ranges))

        serializers = self._serializers(by_name)
        referenced = [s.referenced for s in module.structs] + [
            a.target.referenced for a in module.type_aliases
        ]
        return RenderModule(
            package=module.package.replace(".", "::") if module.package else None,
            dep_includes=[
                d.replace(".", "/") + ".hpp"
                for d in module.imports
                if self._schema.modules[d].types
                or self._schema.modules[d].primitive_aliases
                or self._schema.modules[d].type_aliases
            ],
            primitive_aliases=primitive_aliases,
            type_aliases=type_aliases,
            unversioned=unversioned,
            namespaces=namespaces,
            traits=traits,
            serializers=serializers,
            latest_aliases=[
                t.name for t in module.types if plan.is_versioned(t.name)
            ],
            latest_version=latest_version,
            uses_uuid=any("UUID" in r for r in referenced),
            uses_nbt=any(r & self._schema.builtins for r in referenced),
        )

    # --- type definitions ----------------------------------------------------

    def _definition(
        self, t: Enum | Struct, view: tuple[Any, ...] | None = None
    ) -> RenderEnum | RenderStruct:
        if isinstance(t, Enum):
            return self._enum_def(t, t.members if view is None else view)
        return self._struct_def(t, t.fields if view is None else view)

    def _enum_def(self, enum: Enum, members: Sequence[EnumMember]) -> RenderEnum:
        return RenderEnum(enum.name, [(self._camel(m.name), m.value) for m in members])

    def _struct_def(self, struct: Struct, fields: Sequence[Field]) -> RenderStruct:
        nested = frozenset(e.name for e in struct.enums)
        rendered: list[tuple[str, str]] = []
        for f in fields:
            ctype = self._cpp_type(f.type, nested) if f.type is not None else None
            if ctype is None:  # an unresolvable field: emit a bare struct
                return RenderStruct(struct.name, [], [], [])
            rendered.append((ctype, f.name))
        constants: list[tuple[str, str, str]] = []
        if struct.packet_id is not None:
            constants.append(("Id", "int", str(struct.packet_id)))
        nested_defs = [self._enum_def(e, e.members) for e in struct.enums]
        return RenderStruct(struct.name, nested_defs, constants, rendered)

    def _cpp_type(
        self, type_ref: TypeRef | None, nested: frozenset[str]
    ) -> str | None:
        match type_ref:
            case Primitive(name=name):
                return PRIMITIVE_TYPES.get(name)
            case Named(name=name):
                resolved = (
                    name in nested
                    or name in self._known
                    or name in self._builtins
                )
                return name if resolved else None
            case Optional(inner=inner):
                inner_type = self._cpp_type(inner, nested)
                return None if inner_type is None else f"std::optional<{inner_type}>"
            case Repeated(inner=inner, count=count):
                inner_type = self._cpp_type(inner, nested)
                if inner_type is None:
                    return None
                if count is None:
                    return f"std::vector<{inner_type}>"
                return f"std::array<{inner_type}, {count}>"
            case Mapping(key=key, value=value):
                key_type = self._cpp_type(key, nested)
                value_type = self._cpp_type(value, nested)
                if key_type is None or value_type is None:
                    return None
                return f"std::map<{key_type}, {value_type}>"
            case Variant(arms=arms):
                parts: list[str] = []
                for arm in arms:
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
        self, by_name: dict[str, Enum | Struct]
    ) -> list[RenderSerializer]:
        string_coded = self._string_coded_enums()
        out: list[RenderSerializer] = []
        for name in self._plan.order:
            t = by_name[name]
            snapshots = (
                self._plan.fresh_snapshots(name)
                if self._plan.is_versioned(name)
                else [None]
            )
            if isinstance(t, Enum):
                if name in string_coded:
                    out += [self._enum_serializer(t, s) for s in snapshots]
            else:
                out += filter(None, (self._struct_serializer(t, s) for s in snapshots))
        # Only variant-targeted type aliases need a generated serializer --
        # a `using X = std::variant<...>` resolves `Serializer<X>` to a variant
        # specialization that doesn't exist by default. Other type-alias
        # targets reuse their underlying type's serializer transparently.
        for a in self._module.type_aliases:
            if isinstance(a.target, Variant):
                out.append(self._variant_alias_serializer(a))
        return out

    def _string_coded_enums(self) -> frozenset[str]:
        """Module-scope enums some field encodes by name -- these need a
        `Serializer` specialization. Integer-coded uses inline a cast instead."""
        out: set[str] = set()
        for struct in self._module.structs:
            for f in struct.fields:
                for arm in f.arms:
                    wire = arm.wire
                    while isinstance(wire, (Opt, Cond)):
                        wire = wire.inner
                    if isinstance(wire, EnumRef) and wire.scalar is None:
                        out.add(wire.name)
        return frozenset(out)

    def _struct_serializer(
        self, struct: Struct, snapshot: int | None
    ) -> RenderSerializer | None:
        if snapshot is None:
            fields: Sequence[Field] = struct.fields
            qualified = struct.name
        else:
            fields = self._plan.visible(struct.name, snapshot)
            qualified = f"{self._ns(snapshot)}::{struct.name}"
        wired: list[tuple[Field, Wire]] = []
        for f in fields:
            if f.wire is None:  # an unserializable field skips the whole struct
                return None
            wired.append((f, f.wire))
        self._snap, self._owner = snapshot, qualified
        self._nested = frozenset(e.name for e in struct.enums)
        groups = self._field_groups(wired)

        # The fields of a `with field(when=...)` guard share one `if`; every
        # other field stands alone. The guard `if` is emitted here, around the
        # whole group -- `_write`/`_read` never see the `Cond` wrapper, each
        # field is lowered straight from its inner wire.
        serialize = _Code()
        for guard, group in groups:
            if guard is None:
                ((f, wire),) = group
                self._write(serialize, f.type, wire, f"value.{f.name}")
                continue
            with serialize.block(f"if ({self._predicate(guard, 'value')})"):
                for f, wire in group:
                    assert isinstance(wire, Cond)
                    self._write(serialize, f.type, wire.inner, f"value.{f.name}")

        deserialize = _Code()
        deserialize(f"{qualified} out;")
        for guard, group in groups:
            if guard is None:
                ((f, wire),) = group
                with deserialize.block():
                    self._read(deserialize, f.type, wire, f"out.{f.name}")
                continue
            with deserialize.block(f"if ({self._predicate(guard, 'out')})"):
                for f, wire in group:
                    assert isinstance(wire, Cond)
                    with deserialize.block():
                        self._read(deserialize, f.type, wire.inner, f"out.{f.name}")
        deserialize("return out;")
        return RenderSerializer(
            qualified, f"const {qualified} &value", serialize.lines, deserialize.lines
        )

    @staticmethod
    def _field_groups(
        wired: list[tuple[Field, Wire]],
    ) -> list[tuple[Pred | None, list[tuple[Field, Wire]]]]:
        """Partition a struct's fields into emission groups. Fields from one
        `with field(when=...)` block -- carrying the same `Cond.group` index --
        form one group, emitted under a single shared `if`. Every other field,
        a lone `field(when=...)` included, is its own group; a group with a
        guard predicate is gated, one with None is not."""
        groups: list[tuple[Pred | None, list[tuple[Field, Wire]]]] = []
        open_group: int | None = None
        for f, wire in wired:
            if (
                isinstance(wire, Cond)
                and wire.group is not None
                and wire.group == open_group
            ):
                groups[-1][1].append((f, wire))
                continue
            if isinstance(wire, Cond):
                groups.append((wire.predicate, [(f, wire)]))
                open_group = wire.group
            else:
                groups.append((None, [(f, wire)]))
                open_group = None
        return groups

    def _variant_alias_serializer(self, a: TypeAlias) -> RenderSerializer:
        """A `type Name = A | B | C` alias serializes exactly as an inline
        `A | B | C` field does: the same varuint-tagged `Switch` body, written
        straight from and read straight into the variant itself."""
        assert isinstance(a.target, Variant) and isinstance(a.wire, Switch)
        self._snap, self._owner, self._nested = None, a.name, frozenset()
        serialize = _Code()
        self._write(serialize, a.target, a.wire, "value")
        deserialize = _Code()
        deserialize(f"{a.name} out;")
        self._read(deserialize, a.target, a.wire, "out")
        deserialize("return out;")
        return RenderSerializer(
            a.name, f"const {a.name} &value", serialize.lines, deserialize.lines
        )

    def _enum_serializer(self, enum: Enum, snapshot: int | None) -> RenderSerializer:
        if snapshot is None:
            members, qualified = enum.members, enum.name
        else:
            members = self._plan.visible(enum.name, snapshot)
            qualified = f"{self._ns(snapshot)}::{enum.name}"
        serialize = _Code()
        serialize(f"using E = {qualified};")
        for m in members:
            serialize(
                f"if (value == E::{self._camel(m.name)}) {{ "
                f'stream.write(std::string_view{{"{m.wire_name}"}}); return; }}'
            )
        deserialize = _Code()
        deserialize(f"using E = {qualified};")
        deserialize("auto v = stream.read<std::string>();")
        deserialize("if (!v) return make_unexpected(v.error());")
        for m in members:
            deserialize(f'if (*v == "{m.wire_name}") return E::{self._camel(m.name)};')
        deserialize(
            "return make_unexpected("
            "std::make_error_code(std::errc::illegal_byte_sequence));"
        )
        return RenderSerializer(
            qualified, f"{qualified} value", serialize.lines, deserialize.lines
        )

    def _write(
        self, code: _Code, type_ref: TypeRef | None, wire: Wire, expr: str
    ) -> None:
        match wire:
            case Scalar():
                code(self._scalar_write(wire, expr))
            case Str():
                code(f"stream.write({expr});")
            case StructRef(name=name):
                code(f"Serializer<{self._type_at(name)}>::serialize(stream, {expr});")
            case EnumRef(name=name, scalar=None):
                code(f"Serializer<{self._type_at(name)}>::serialize(stream, {expr});")
            case EnumRef(scalar=Scalar() as scalar):
                code(self._scalar_write(scalar, expr))
            case Opt(inner=inner, discriminator=discriminator, present_tag=present):
                if discriminator:
                    code(f"stream.writeVarInt<std::uint32_t>"
                         f"({expr}.has_value() ? {present}u : {1 - present}u);")
                else:
                    code(f"stream.write<bool>({expr}.has_value());")
                assert isinstance(type_ref, Optional)
                with code.block(f"if ({expr}.has_value())"):
                    self._write(code, type_ref.inner, inner, f"*{expr}")
            case Repeat(inner=inner, prefix=prefix):
                assert isinstance(type_ref, Repeated)
                depth = self._rep
                self._rep += 1
                if prefix is not None:
                    code(self._scalar_write(prefix, f"{expr}.size()"))
                with code.block(f"for (const auto &e{depth} : {expr})"):
                    self._write(code, type_ref.inner, inner, f"e{depth}")
                self._rep -= 1
            case Map(key=key, value=value, prefix=prefix):
                assert isinstance(type_ref, Mapping)
                depth = self._rep
                self._rep += 1
                code(self._scalar_write(prefix, f"{expr}.size()"))
                with code.block(f"for (const auto &[k{depth}, v{depth}] : {expr})"):
                    self._write(code, type_ref.key, key, f"k{depth}")
                    self._write(code, type_ref.value, value, f"v{depth}")
                self._rep -= 1
            case Switch(arms=arms):
                assert isinstance(type_ref, Variant)
                # `expr` may be a dereference (`*value.x`) when the Switch sits
                # inside an Opt -- parenthesize before the `.index()` postfix.
                code(f"stream.writeVarInt<std::uint32_t>(({expr}).index());")
                with code.block(f"switch (({expr}).index())"):
                    for index, arm in enumerate(arms):
                        with code.block(f"case {index}:"):
                            if arm is not None:
                                self._write(
                                    code, type_ref.arms[index], arm,
                                    f"std::get<{index}>({expr})",
                                )
                            code("break;")

    def _read(
        self, code: _Code, type_ref: TypeRef | None, wire: Wire, target: str
    ) -> None:
        match wire:
            case Scalar():
                self._scalar_read(code, wire)
                cast = self._cpp_type(type_ref, self._nested)
                code(f"{target} = static_cast<{cast}>(*v);")
            case Str():
                code("auto v = stream.read<std::string>();")
                code("if (!v) return make_unexpected(v.error());")
                code(f"{target} = *v;")
            case StructRef(name=name) | EnumRef(name=name, scalar=None):
                code(f"auto v = Serializer<{self._type_at(name)}>::deserialize(stream);")
                code("if (!v) return make_unexpected(v.error());")
                code(f"{target} = *v;")
            case EnumRef(name=name, scalar=Scalar() as scalar):
                self._scalar_read(code, scalar)
                code(f"{target} = static_cast<{self._type_at(name)}>(*v);")
            case Opt(inner=inner, discriminator=discriminator, present_tag=present):
                holder = "tag" if discriminator else "present"
                verb = (
                    "readVarInt<std::uint32_t>" if discriminator else "read<bool>"
                )
                guard = f"*tag == {present}" if discriminator else "*present"
                code(f"auto {holder} = stream.{verb}();")
                code(f"if (!{holder}) return make_unexpected({holder}.error());")
                assert isinstance(type_ref, Optional)
                with code.block(f"if ({guard})"):
                    self._read(code, type_ref.inner, inner, target)
            case Repeat(inner=inner, prefix=prefix, count=count):
                assert isinstance(type_ref, Repeated)
                depth = self._rep
                self._rep += 1
                if prefix is not None:
                    u = PRIMITIVE_TYPES[prefix.primitive]
                    verb = f"readVarInt<{u}>" if prefix.varint else f"read<{u}>"
                    code(f"auto len{depth} = stream.{verb}();")
                    code(f"if (!len{depth}) return make_unexpected(len{depth}.error());")
                    code(f"{target}.clear();")
                    head = (
                        f"for (auto rep{depth} = *len{depth}; "
                        f"rep{depth} > 0; --rep{depth})"
                    )
                    with code.block(head):
                        code(f"{target}.emplace_back();")
                        self._read(code, type_ref.inner, inner, f"{target}.back()")
                else:
                    head = (
                        f"for (std::size_t i{depth} = 0; "
                        f"i{depth} < {count}; ++i{depth})"
                    )
                    with code.block(head):
                        self._read(code, type_ref.inner, inner, f"{target}[i{depth}]")
                self._rep -= 1
            case Map(key=key, value=value, prefix=prefix):
                assert isinstance(type_ref, Mapping)
                depth = self._rep
                self._rep += 1
                u = PRIMITIVE_TYPES[prefix.primitive]
                verb = f"readVarInt<{u}>" if prefix.varint else f"read<{u}>"
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
                        self._read(code, type_ref.key, key, f"k{depth}")
                    code(f"{holder}::mapped_type v{depth}{{}};")
                    with code.block():
                        self._read(code, type_ref.value, value, f"v{depth}")
                    code(f"{target}.emplace(k{depth}, v{depth});")
                self._rep -= 1
            case Switch(arms=arms):
                assert isinstance(type_ref, Variant)
                depth = self._rep
                self._rep += 1
                # Decode into a local variant of the alias/field's own type,
                # then assign -- `target` may be a std::optional<variant> when
                # the Switch sits inside an Opt, so it cannot be emplaced into.
                vartype = self._cpp_type(type_ref, self._nested)
                assert vartype is not None
                code(f"auto tag{depth} = stream.readVarInt<std::uint32_t>();")
                code(f"if (!tag{depth}) return make_unexpected(tag{depth}.error());")
                code(f"{vartype} var{depth}{{}};")
                with code.block(f"switch (*tag{depth})"):
                    for index, arm in enumerate(arms):
                        with code.block(f"case {index}:"):
                            code(
                                f"std::variant_alternative_t<{index}, {vartype}> "
                                f"arm{depth}{{}};"
                            )
                            if arm is not None:
                                with code.block():
                                    self._read(
                                        code, type_ref.arms[index], arm,
                                        f"arm{depth}",
                                    )
                            code(f"var{depth}.emplace<{index}>(arm{depth});")
                            code("break;")
                    with code.block("default:"):
                        code(
                            "return make_unexpected(std::make_error_code("
                            "std::errc::illegal_byte_sequence));"
                        )
                code(f"{target} = var{depth};")
                self._rep -= 1

    def _predicate(self, pred: Pred, base: str) -> str:
        """Render a `when=` predicate as a C++ boolean expression. `base` is
        the struct accessor -- `value` when serializing, `out` when reading."""
        match pred:
            case PredField(name=name):
                return f"{base}.{name}"
            case PredInt(value=value):
                return str(value)
            case PredEnum(enum=enum, member=member):
                return f"{self._type_at(enum)}::{self._camel(member)}"
            case PredNot(operand=operand):
                return f"!({self._predicate(operand, base)})"
            case PredAnd(operands=operands):
                return " && ".join(f"({self._predicate(o, base)})" for o in operands)
            case PredOr(operands=operands):
                return " || ".join(f"({self._predicate(o, base)})" for o in operands)
            case PredCompare(op=op, left=left, right=right):
                return (
                    f"({self._predicate(left, base)}) {op} "
                    f"({self._predicate(right, base)})"
                )

    @staticmethod
    def _scalar_write(scalar: Scalar, expr: str) -> str:
        u = PRIMITIVE_TYPES[scalar.primitive]
        if scalar.varint:
            return f"stream.writeVarInt<{u}>({expr});"
        if scalar.big_endian:
            return f"stream.write<{u}, std::endian::big>({expr});"
        return f"stream.write<{u}>({expr});"

    @staticmethod
    def _scalar_read(code: _Code, scalar: Scalar) -> None:
        u = PRIMITIVE_TYPES[scalar.primitive]
        if scalar.varint:
            code(f"auto v = stream.readVarInt<{u}>();")
        elif scalar.big_endian:
            code(f"auto v = stream.read<{u}, std::endian::big>();")
        else:
            code(f"auto v = stream.read<{u}>();")
        code("if (!v) return make_unexpected(v.error());")

    def _type_at(self, name: str) -> str:
        """A referenced type's qualified name from a serializer at `self._snap`."""
        if name in self._nested:
            return f"{self._owner}::{name}"
        if self._plan.is_versioned(name):
            assert self._snap is not None
            return f"{self._ns(self._plan.concrete(name, self._snap))}::{name}"
        return name

    # --- validation ----------------------------------------------------------

    def _guard_cross_module(self) -> None:
        """A reference to a versioned type in another module would need the two
        headers' snapshot sets aligned -- unsupported. Unversioned cross-module
        references (`Vec3`, primitives) are fine."""
        dep_versioned: set[str] = set()
        for dep in self._module.imports:
            mod = self._schema.modules.get(dep)
            if mod is not None:
                dep_versioned |= {t.name for t in mod.types if t.change_points}
        if not dep_versioned:
            return
        for struct in self._module.structs:
            bad = struct.referenced & dep_versioned
            if bad:
                raise CompilerError(
                    f"{struct.name}: references versioned type(s) {sorted(bad)} "
                    f"from another module -- cross-module versioning is unsupported"
                )

    # --- spellings -----------------------------------------------------------

    @staticmethod
    def _ns(version: int) -> str:
        return "base" if version == 0 else f"v{version}"

    @staticmethod
    def _camel(name: str) -> str:
        return inflection.camelize(name.lower())

    @staticmethod
    def _clause(lo: int, hi: int | None) -> str:
        parts: list[str] = []
        if lo:
            parts.append(f"V >= {lo}")
        if hi is not None:
            parts.append(f"V < {hi}")
        return " && ".join(parts)
