"""Field-type C++ spelling + the `FieldGenerator` codec hierarchy.

protoc analog: `compiler/cpp/cpp_field.{h,cc}` plus the per-type field
generators (`primitive_field`, `string_field`, `enum_field`, `message_field`,
`repeated_*`). `FieldGeneratorMap` is protoc's per-message map from a field to
its generator; `make_field_generator` is the factory behind it, which
walks a `FieldType` and builds a generator tree whose combinator nodes
(optional / repeated / map / variant) hold a child generator and recurse.

`cpp_type()` is the shared type-spelling used by field declarations and
`type`-alias rendering. `FileContext` is the cross-cutting state every
generator reads.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from bedrock_protocol.descriptor import (
    VARINT_PRIMITIVES,
    BitsetType,
    CompilerError,
    CondType,
    EnumType,
    Field,
    FieldType,
    LiteralType,
    MappingType,
    OptionalType,
    Predicate,
    PrimitiveType,
    RepeatedType,
    ResolvedFile,
    Struct,
    StructType,
    VariantType,
)

from .helpers import PRIMITIVE_TYPES, cpp_qualified, outermost
from .printer import Printer


@dataclass(frozen=True)
class FileContext:
    """Cross-cutting state shared across the per-construct generators."""

    resolved: ResolvedFile
    known: frozenset[str]
    string_coded_enums: frozenset[str]

    @property
    def package(self) -> str | None:
        """The namespace the file's declarations live in, which anchors a
        reference out of the pre-cereal tree."""
        return self.resolved.file.package


# --- type spelling ------------------------------------------------------------


def cpp_type(
    t: FieldType | None, ctx: FileContext, snapshot: int | None = None, owner: str | None = None
) -> str | None:
    """C++ spelling for a field-type node, or None if unresolvable. When
    `snapshot` is set, versioned struct / enum references are snapshot-qualified
    (`v1001::EnvironmentAttributeData`). Inside a namespace that already holds
    the right view, pass `snapshot=None` and let unqualified lookup work.

    `owner` is the flavour scope of the declaration doing the referencing, which
    decides whether a cross-tree reference needs qualifying."""
    if t is None:
        return None
    if isinstance(t, PrimitiveType):
        return t.alias if t.alias is not None else PRIMITIVE_TYPES.get(t.name)
    if isinstance(t, (StructType, EnumType)):
        if t.name not in ctx.known:
            return None
        root = outermost(t.name)
        if snapshot is not None and ctx.resolved.is_versioned(root):
            view = ctx.resolved.present_at(root, snapshot)
            if view is not None:
                return cpp_qualified(t.name, view.concrete, owner=owner, package=ctx.package)
        return cpp_qualified(t.name, owner=owner, package=ctx.package)
    if isinstance(t, LiteralType):
        # A constant lives on the wire only -- no member spells it in C++.
        return None
    if isinstance(t, BitsetType):
        return f"std::bitset<{t.size}>"
    if isinstance(t, OptionalType):
        inner = cpp_type(t.inner, ctx, snapshot, owner)
        return None if inner is None else f"std::optional<{inner}>"
    if isinstance(t, RepeatedType):
        inner = cpp_type(t.inner, ctx, snapshot, owner)
        return None if inner is None else f"std::vector<{inner}>"
    if isinstance(t, MappingType):
        key = cpp_type(t.key, ctx, snapshot, owner)
        value = cpp_type(t.value, ctx, snapshot, owner)
        return None if key is None or value is None else f"std::map<{key}, {value}>"
    if isinstance(t, VariantType):
        parts: list[str] = []
        for case in t.cases:
            if case is None:
                parts.append("std::monostate")
                continue
            spelled = cpp_type(case, ctx, snapshot, owner)
            if spelled is None:
                return None
            parts.append(spelled)
        return f"std::variant<{', '.join(parts)}>"
    if isinstance(t, CondType):
        # A gated field carries no presence marker: it is spelled as its bare
        # payload and left default-constructed when the predicate is false.
        return cpp_type(t.inner, ctx, snapshot, owner)
    return None


def render_predicate(
    pred: Predicate, base: str, ctx: FileContext, snapshot: int | None, owner: str | None = None
) -> str:
    """A `when=` predicate as a C++ boolean expression. `base` is the struct
    variable its field references hang off — `value` writing, `out` reading."""

    def go(node: Predicate) -> str:
        if node.kind == "field":
            return f"{base}.{node.text}"
        if node.kind == "int":
            return node.text
        if node.kind == "enum":
            enum, member = node.text.rsplit(".", 1)
            return f"{qualified_at(enum, ctx, snapshot, owner)}::{member}"
        if node.kind == "len":
            return f"{go(node.operands[0])}.size()"
        if node.kind == "bittest":
            return f"{base}.{node.text}.test(static_cast<std::size_t>({go(node.operands[0])}))"
        if node.kind == "not":
            return f"!({go(node.operands[0])})"
        op = {"and": "&&", "or": "||"}.get(node.kind, node.kind)
        return f" {op} ".join(f"({go(o)})" for o in node.operands)

    return go(pred)


def qualified_at(name: str, ctx: FileContext, snapshot: int | None, owner: str | None = None) -> str:
    """Qualified spelling of a struct/enum ref from inside a serializer at
    `snapshot` (emitted at namespace scope, so versioned refs need the `vN::`)."""
    if ctx.resolved.is_versioned(outermost(name)):
        assert snapshot is not None
        view = ctx.resolved.present_at(outermost(name), snapshot)
        assert view is not None
        return cpp_qualified(name, view.concrete, owner=owner, package=ctx.package)
    return cpp_qualified(name, owner=owner, package=ctx.package)


# --- primitive wire helpers ---------------------------------------------------


def _order_argument(prim: PrimitiveType) -> str:
    """The stream's explicit byte-order template argument, empty for the default."""
    return ", std::endian::big" if prim.endian == "big" else ""


def _primitive_write(prim: PrimitiveType, expr: str) -> str:
    if prim.encoding in ("str", "bytes"):
        return f"stream.write({expr});"
    u = PRIMITIVE_TYPES[prim.encoding]
    if prim.encoding in VARINT_PRIMITIVES:
        return f"stream.writeVarInt<{u}>({expr});"
    return f"stream.write<{u}{_order_argument(prim)}>({expr});"


def _primitive_read(prim: PrimitiveType) -> str:
    if prim.encoding in ("str", "bytes"):
        return "auto v = stream.read<std::string>();"
    u = PRIMITIVE_TYPES[prim.encoding]
    if prim.encoding in VARINT_PRIMITIVES:
        return f"auto v = stream.readVarInt<{u}>();"
    return f"auto v = stream.read<{u}{_order_argument(prim)}>();"


def _read_verb(prim: PrimitiveType) -> str:
    u = PRIMITIVE_TYPES[prim.encoding]
    if prim.encoding in VARINT_PRIMITIVES:
        return f"readVarInt<{u}>"
    return f"read<{u}{_order_argument(prim)}>"


def _literal_value(value: bool | int) -> str:
    """A `Literal[...]` member as a C++ literal."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _codec_includes(prim: PrimitiveType) -> set[str]:
    """Headers a primitive's read / write needs — its own, plus `<bit>` where the
    call spells a byte order."""
    own = {"<bit>"} if prim.endian == "big" else set()
    return type_includes(prim) | own


def type_includes(t: FieldType | None) -> set[str]:
    """Headers a type's C++ spelling needs: `std::vector<...>` -> `<vector>`,
    a `std::int32_t` field -> `<cstdint>`, and so on. Struct/enum references
    carry no stdlib header."""
    if isinstance(t, PrimitiveType):
        if t.name in ("str", "bytes"):
            return {"<string>"}
        # the codec names the encoding's C++ type too, which may be the wider one
        if any(PRIMITIVE_TYPES[n].startswith("std::") for n in (t.name, t.encoding)):
            return {"<cstdint>"}
        return set()
    if isinstance(t, BitsetType):
        return {"<bitset>"}
    if isinstance(t, OptionalType):
        return {"<optional>"} | type_includes(t.inner)
    if isinstance(t, RepeatedType):
        return {"<vector>"} | type_includes(t.inner)
    if isinstance(t, MappingType):
        return {"<map>"} | type_includes(t.key) | type_includes(t.value)
    if isinstance(t, VariantType):
        out = {"<variant>"}
        for c in t.cases:
            if c is not None:
                out |= type_includes(c)
        return out
    if isinstance(t, CondType):
        return type_includes(t.inner)
    return set()


# --- generator context + hierarchy --------------------------------------------


@dataclass(frozen=True)
class GenContext:
    """State a `FieldGenerator` needs to spell snapshot-qualified references."""

    ctx: FileContext
    snapshot: int | None
    owner: str | None = None


class FieldGenerator(ABC):
    """One wire node's codec. `generate_serialize` pushes `var` onto the
    stream; `generate_deserialize` pulls from the stream into `target`. `depth`
    disambiguates the loop / temporary names of nested combinators."""

    @abstractmethod
    def generate_serialize(self, p: Printer, var: str, depth: int = 0) -> None: ...

    @abstractmethod
    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None: ...


class PrimitiveFieldGenerator(FieldGenerator):
    def __init__(self, prim: PrimitiveType, gc: GenContext) -> None:
        self._prim = prim
        self._gc = gc

    def generate_serialize(self, p: Printer, var: str, depth: int = 0) -> None:
        p.add_includes(*_codec_includes(self._prim))
        p.print(_primitive_write(self._prim, var) + "\n")

    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None:
        p.add_includes("<expected>", *_codec_includes(self._prim))
        p.print(_primitive_read(self._prim) + "\n")
        p.print("if (!v) return std::unexpected(v.error());\n")
        if self._prim.name in ("str", "bytes") and self._prim.alias is None:
            p.print(f"{target} = *v;\n")
        else:
            cast = cpp_type(self._prim, self._gc.ctx)
            p.print(f"{target} = static_cast<{cast}>(*v);\n")


class EnumFieldGenerator(FieldGenerator):
    def __init__(self, enum_type: EnumType, gc: GenContext) -> None:
        self._enum = enum_type
        self._gc = gc

    def _qualified(self) -> str:
        return qualified_at(self._enum.name, self._gc.ctx, self._gc.snapshot, self._gc.owner)

    def generate_serialize(self, p: Printer, var: str, depth: int = 0) -> None:
        if self._enum.scalar is None:
            p.add_includes("<bedrock/serializer.hpp>")
            p.print(f"Serializer<{self._qualified()}>::serialize(stream, {var});\n")
        else:
            p.add_includes(*_codec_includes(self._enum.scalar))
            p.print(_primitive_write(self._enum.scalar, var) + "\n")

    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None:
        p.add_includes("<expected>")
        if self._enum.scalar is None:
            p.add_includes("<bedrock/serializer.hpp>")
            p.print(f"auto v = Serializer<{self._qualified()}>::deserialize(stream);\n")
            p.print("if (!v) return std::unexpected(v.error());\n")
            p.print(f"{target} = *v;\n")
        else:
            p.add_includes(*_codec_includes(self._enum.scalar))
            p.print(_primitive_read(self._enum.scalar) + "\n")
            p.print("if (!v) return std::unexpected(v.error());\n")
            p.print(f"{target} = static_cast<{self._qualified()}>(*v);\n")


class ClassFieldGenerator(FieldGenerator):
    def __init__(self, struct_type: StructType, gc: GenContext) -> None:
        self._struct = struct_type
        self._gc = gc

    def _qualified(self) -> str:
        return qualified_at(self._struct.name, self._gc.ctx, self._gc.snapshot, self._gc.owner)

    def generate_serialize(self, p: Printer, var: str, depth: int = 0) -> None:
        p.add_includes("<bedrock/serializer.hpp>")
        p.print(f"Serializer<{self._qualified()}>::serialize(stream, {var});\n")

    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None:
        p.add_includes("<bedrock/serializer.hpp>", "<expected>")
        p.print(f"auto v = Serializer<{self._qualified()}>::deserialize(stream);\n")
        p.print("if (!v) return std::unexpected(v.error());\n")
        p.print(f"{target} = *v;\n")


class BitsetFieldGenerator(FieldGenerator):
    """`bitset[N]` — the base-128 dump. The codec is hand-written in
    <bedrock/bitset.hpp> rather than emitted here: N may exceed any integer's
    width, so the loop is over bits and there is nothing per-schema about it."""

    def __init__(self, bits: BitsetType) -> None:
        self._bits = bits

    @property
    def _spelling(self) -> str:
        return f"std::bitset<{self._bits.size}>"

    def _includes(self) -> tuple[str, ...]:
        return ("<bitset>", "<bedrock/bitset.hpp>", "<bedrock/serializer.hpp>")

    def generate_serialize(self, p: Printer, var: str, depth: int = 0) -> None:
        p.add_includes(*self._includes())
        p.print(f"Serializer<{self._spelling}>::serialize(stream, {var});\n")

    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None:
        p.add_includes("<expected>", *self._includes())
        p.print(f"auto v = Serializer<{self._spelling}>::deserialize(stream);\n")
        p.print("if (!v) return std::unexpected(v.error());\n")
        p.print(f"{target} = *v;\n")


class OptionalFieldGenerator(FieldGenerator):
    """`T | None` — a bool presence flag then the payload. The read stages through
    a temporary of the payload type: a container payload fills itself via
    `.clear()` / `.emplace_back()`, which the target `std::optional` has no members
    for, so it is built first and then moved in. `value_type` is that payload's
    C++ spelling."""

    def __init__(self, inner: FieldGenerator, value_type: str, gc: GenContext) -> None:
        self._inner = inner
        self._value_type = value_type
        self._gc = gc

    def generate_serialize(self, p: Printer, var: str, depth: int = 0) -> None:
        p.print(f"stream.write<bool>({var}.has_value());\n")
        with p.block(f"if ({var}.has_value())"):
            self._inner.generate_serialize(p, f"(*{var})", depth)

    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None:
        p.add_includes("<expected>")
        p.print("auto present = stream.read<bool>();\n")
        p.print("if (!present) return std::unexpected(present.error());\n")
        with p.block("if (*present)"):
            p.print(f"{self._value_type} staged{{}};\n")
            self._inner.generate_deserialize(p, "staged", depth)
            p.print(f"{target} = std::move(staged);\n")


class LiteralFieldGenerator(FieldGenerator):
    """`Literal[V, ...]` — a constant on the wire and nothing in memory, so both
    halves ignore the struct: the write emits the value, and the read rejects
    anything the annotation does not list."""

    def __init__(self, literal: LiteralType) -> None:
        self._literal = literal

    def generate_serialize(self, p: Printer, var: str, depth: int = 0) -> None:
        p.add_includes(*_codec_includes(self._literal.wire))
        p.print(_primitive_write(self._literal.wire, _literal_value(self._literal.written)) + "\n")

    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None:
        p.add_includes("<expected>", "<system_error>", *_codec_includes(self._literal.wire))
        p.print(_primitive_read(self._literal.wire) + "\n")
        p.print("if (!v) return std::unexpected(v.error());\n")
        accepted = " && ".join(f"*v != {_literal_value(value)}" for value in self._literal.values)
        with p.block(f"if ({accepted})"):
            p.print("return std::unexpected(std::make_error_code(std::errc::illegal_byte_sequence));\n")


class RepeatedFieldGenerator(FieldGenerator):
    """`list[T]`: a length prefix then the elements. A `count=` list carries no
    prefix -- the length is an expression over earlier fields of the surrounding
    struct, which the read recomputes from what it has already filled in."""

    def __init__(
        self,
        inner: FieldGenerator,
        prefix: PrimitiveType,
        gc: GenContext,
        count: Predicate | None = None,
    ) -> None:
        self._inner = inner
        self._prefix = prefix
        self._gc = gc
        self._count = count

    def generate_serialize(self, p: Printer, var: str, depth: int = 0) -> None:
        if self._count is None:
            p.add_includes(*type_includes(self._prefix))
            p.print(_primitive_write(self._prefix, f"{var}.size()") + "\n")
        with p.block(f"for (const auto &e{depth} : {var})"):
            self._inner.generate_serialize(p, f"e{depth}", depth + 1)

    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None:
        p.add_includes("<expected>")
        if self._count is not None:
            # The count reads the surrounding struct's earlier fields, which
            # `MessageGenerator` names `out` -- not `target`, which is a staging
            # temporary whenever the list sits inside another combinator.
            count = render_predicate(self._count, "out", self._gc.ctx, self._gc.snapshot, self._gc.owner)
            p.print(f"{target}.clear();\n")
            with p.block(f"for (auto rep{depth} = {count}; rep{depth} > 0; --rep{depth})"):
                p.print(f"{target}.emplace_back();\n")
                self._inner.generate_deserialize(p, f"{target}.back()", depth + 1)
            return
        p.add_includes(*type_includes(self._prefix))
        p.print(f"auto len{depth} = stream.{_read_verb(self._prefix)}();\n")
        p.print(f"if (!len{depth}) return std::unexpected(len{depth}.error());\n")
        p.print(f"{target}.clear();\n")
        with p.block(f"for (auto rep{depth} = *len{depth}; rep{depth} > 0; --rep{depth})"):
            p.print(f"{target}.emplace_back();\n")
            self._inner.generate_deserialize(p, f"{target}.back()", depth + 1)


class MapFieldGenerator(FieldGenerator):
    """`dict[K, V]`: a length prefix then that many key/value pairs. The key
    read is brace-scoped so its temporary cannot collide with the value's."""

    def __init__(
        self,
        key: FieldGenerator,
        value: FieldGenerator,
        prefix: PrimitiveType,
        key_type: str,
        gc: GenContext,
    ) -> None:
        self._key = key
        self._value = value
        self._prefix = prefix
        self._key_type = key_type
        self._gc = gc

    def generate_serialize(self, p: Printer, var: str, depth: int = 0) -> None:
        p.add_includes("<map>", *type_includes(self._prefix))
        p.print(_primitive_write(self._prefix, f"{var}.size()") + "\n")
        with p.block(f"for (const auto &[k{depth}, v{depth}] : {var})"):
            self._key.generate_serialize(p, f"k{depth}", depth + 1)
            self._value.generate_serialize(p, f"v{depth}", depth + 1)

    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None:
        p.add_includes("<expected>", "<map>", *type_includes(self._prefix))
        p.print(f"auto len{depth} = stream.{_read_verb(self._prefix)}();\n")
        p.print(f"if (!len{depth}) return std::unexpected(len{depth}.error());\n")
        p.print(f"{target}.clear();\n")
        with p.block(f"for (auto rep{depth} = *len{depth}; rep{depth} > 0; --rep{depth})"):
            p.print(f"{self._key_type} key{depth}{{}};\n")
            with p.block(""):
                self._key.generate_deserialize(p, f"key{depth}", depth + 1)
            self._value.generate_deserialize(p, f"{target}[key{depth}]", depth + 1)


class VariantFieldGenerator(FieldGenerator):
    def __init__(
        self,
        cases: list[FieldGenerator | None],
        discriminator: PrimitiveType,
        variant_type: str,
        gc: GenContext,
    ) -> None:
        self._cases = cases
        self._disc = discriminator
        self._variant_type = variant_type
        self._gc = gc

    def generate_serialize(self, p: Printer, var: str, depth: int = 0) -> None:
        p.add_includes("<variant>", *type_includes(self._disc))
        p.print(_primitive_write(self._disc, f"({var}).index()") + "\n")
        with p.block(f"switch (({var}).index())"):
            for index, case in enumerate(self._cases):
                with p.block(f"case {index}:"):
                    if case is not None:
                        case.generate_serialize(p, f"std::get<{index}>({var})", depth + 1)
                    p.print("break;\n")

    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None:
        p.add_includes("<variant>", "<system_error>", "<expected>", *type_includes(self._disc))
        p.print(f"auto tag{depth} = stream.{_read_verb(self._disc)}();\n")
        p.print(f"if (!tag{depth}) return std::unexpected(tag{depth}.error());\n")
        p.print(f"{self._variant_type} var{depth}{{}};\n")
        with p.block(f"switch (*tag{depth})"):
            for index, case in enumerate(self._cases):
                with p.block(f"case {index}:"):
                    p.print(f"std::variant_alternative_t<{index}, {self._variant_type}> alt{depth}{{}};\n")
                    if case is not None:
                        with p.block(""):
                            case.generate_deserialize(p, f"alt{depth}", depth + 1)
                    p.print(f"var{depth}.emplace<{index}>(alt{depth});\n")
                    p.print("break;\n")
            with p.block("default:"):
                p.print("return std::unexpected(std::make_error_code(std::errc::illegal_byte_sequence));\n")
        p.print(f"{target} = var{depth};\n")


class FieldGeneratorMap:
    """One struct's fields, each mapped to its codec generator — protoc's
    `FieldGeneratorMap`. Built once per message, then indexed: `get(field)` is
    protoc's `field_generators_.get(field)`.

    The struct must be a snapshot view, where each field name appears once."""

    def __init__(self, struct: Struct, ctx: FileContext, snapshot: int | None, owner: str | None = None) -> None:
        gc = GenContext(ctx, snapshot, owner)
        self._by_name: dict[str, FieldGenerator] = {}
        for f in struct.fields:
            (version,) = f.versions
            assert version.type is not None
            self._by_name[f.name] = make_field_generator(version.type, gc)

    def get(self, field: Field) -> FieldGenerator:
        return self._by_name[field.name]


def make_field_generator(t: FieldType, gc: GenContext) -> FieldGenerator:
    """Build the codec generator for one wire node, recursing through combinators."""
    if isinstance(t, PrimitiveType):
        return PrimitiveFieldGenerator(t, gc)
    if isinstance(t, EnumType):
        return EnumFieldGenerator(t, gc)
    if isinstance(t, StructType):
        return ClassFieldGenerator(t, gc)
    if isinstance(t, LiteralType):
        return LiteralFieldGenerator(t)
    if isinstance(t, BitsetType):
        return BitsetFieldGenerator(t)
    if isinstance(t, OptionalType):
        value_type = cpp_type(t.inner, gc.ctx, gc.snapshot, gc.owner)
        assert value_type is not None
        return OptionalFieldGenerator(make_field_generator(t.inner, gc), value_type, gc)
    if isinstance(t, RepeatedType):
        return RepeatedFieldGenerator(make_field_generator(t.inner, gc), t.prefix, gc, t.count)
    if isinstance(t, MappingType):
        key_type = cpp_type(t.key, gc.ctx, gc.snapshot, gc.owner)
        assert key_type is not None
        return MapFieldGenerator(
            make_field_generator(t.key, gc),
            make_field_generator(t.value, gc),
            t.prefix,
            key_type,
            gc,
        )
    if isinstance(t, VariantType):
        cases = [None if c is None else make_field_generator(c, gc) for c in t.cases]
        variant_type = cpp_type(t, gc.ctx, gc.snapshot, gc.owner)
        assert variant_type is not None
        return VariantFieldGenerator(cases, t.discriminator, variant_type, gc)
    if isinstance(t, CondType):
        # The `if` belongs to the struct, not the field: `MessageGenerator` emits
        # it around the whole guarded group, so the codec here is the payload's.
        return make_field_generator(t.inner, gc)
    raise CompilerError(f"no field generator for {t!r}")
