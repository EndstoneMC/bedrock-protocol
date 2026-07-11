"""Field-type C++ spelling + the `FieldGenerator` codec hierarchy.

protoc analog: `compiler/cpp/cpp_field.{h,cc}` plus the per-type field
generators (`primitive_field`, `string_field`, `enum_field`, `message_field`,
`repeated_*`). `make_field_generator` is the `FieldGeneratorMap` factory: it
walks a `FieldType` and builds a generator tree whose combinator nodes
(optional / repeated / variant) hold a child generator and recurse.

`cpp_type()` is the shared type-spelling used by field declarations and
`type`-alias rendering. `FileContext` is the cross-cutting state every
generator reads.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from bedrock_protocol.descriptor import (
    VARINT_PRIMITIVES,
    CompilerError,
    EnumType,
    FieldType,
    OptionalType,
    PrimitiveType,
    RepeatedType,
    ResolvedFile,
    StructType,
    VariantType,
)

from .names import PRIMITIVE_TYPES, snapshot_namespace
from .printer import Printer


@dataclass(frozen=True)
class FileContext:
    """Cross-cutting state shared across the per-construct generators."""

    resolved: ResolvedFile
    known: frozenset[str]
    string_coded_enums: frozenset[str]


# --- type spelling ------------------------------------------------------------


def cpp_type(t: FieldType | None, ctx: FileContext, snapshot: int | None = None) -> str | None:
    """C++ spelling for a field-type node, or None if unresolvable. When
    `snapshot` is set, versioned struct / enum references are snapshot-qualified
    (`v1001::EnvironmentAttributeData`). Inside a namespace that already holds
    the right view, pass `snapshot=None` and let unqualified lookup work."""
    if t is None:
        return None
    if isinstance(t, PrimitiveType):
        return t.alias if t.alias is not None else PRIMITIVE_TYPES.get(t.name)
    if isinstance(t, (StructType, EnumType)):
        if t.name not in ctx.known:
            return None
        if snapshot is not None and ctx.resolved.is_versioned(t.name):
            view = ctx.resolved.present_at(t.name, snapshot)
            if view is not None:
                return f"{snapshot_namespace(view.concrete)}::{t.name}"
        return t.name
    if isinstance(t, OptionalType):
        inner = cpp_type(t.inner, ctx, snapshot)
        return None if inner is None else f"std::optional<{inner}>"
    if isinstance(t, RepeatedType):
        inner = cpp_type(t.inner, ctx, snapshot)
        return None if inner is None else f"std::vector<{inner}>"
    if isinstance(t, VariantType):
        parts: list[str] = []
        for case in t.cases:
            if case is None:
                parts.append("std::monostate")
                continue
            spelled = cpp_type(case, ctx, snapshot)
            if spelled is None:
                return None
            parts.append(spelled)
        return f"std::variant<{', '.join(parts)}>"
    return None


def qualified_at(name: str, ctx: FileContext, snapshot: int | None) -> str:
    """Qualified spelling of a struct/enum ref from inside a serializer at
    `snapshot` (emitted at namespace scope, so versioned refs need the `vN::`)."""
    if ctx.resolved.is_versioned(name):
        assert snapshot is not None
        view = ctx.resolved.present_at(name, snapshot)
        assert view is not None
        return f"{snapshot_namespace(view.concrete)}::{name}"
    return name


# --- primitive wire helpers ---------------------------------------------------


def _primitive_write(prim: PrimitiveType, expr: str) -> str:
    if prim.name in ("str", "bytes"):
        return f"stream.write({expr});"
    u = PRIMITIVE_TYPES[prim.name]
    if prim.name in VARINT_PRIMITIVES:
        return f"stream.writeVarInt<{u}>({expr});"
    return f"stream.write<{u}>({expr});"


def _primitive_read(prim: PrimitiveType) -> str:
    if prim.name in ("str", "bytes"):
        return "auto v = stream.read<std::string>();"
    u = PRIMITIVE_TYPES[prim.name]
    if prim.name in VARINT_PRIMITIVES:
        return f"auto v = stream.readVarInt<{u}>();"
    return f"auto v = stream.read<{u}>();"


def _read_verb(prim: PrimitiveType) -> str:
    u = PRIMITIVE_TYPES[prim.name]
    return f"readVarInt<{u}>" if prim.name in VARINT_PRIMITIVES else f"read<{u}>"


def type_includes(t: FieldType | None) -> set[str]:
    """Headers a type's C++ spelling needs: `std::vector<...>` -> `<vector>`,
    a `std::int32_t` field -> `<cstdint>`, and so on. Struct/enum references
    carry no stdlib header."""
    if isinstance(t, PrimitiveType):
        if t.name in ("str", "bytes"):
            return {"<string>"}
        if PRIMITIVE_TYPES[t.name].startswith("std::"):
            return {"<cstdint>"}
        return set()
    if isinstance(t, OptionalType):
        return {"<optional>"} | type_includes(t.inner)
    if isinstance(t, RepeatedType):
        return {"<vector>"} | type_includes(t.inner)
    if isinstance(t, VariantType):
        out = {"<variant>"}
        for c in t.cases:
            if c is not None:
                out |= type_includes(c)
        return out
    return set()


# --- generator context + hierarchy --------------------------------------------


@dataclass(frozen=True)
class GenContext:
    """State a `FieldGenerator` needs to spell snapshot-qualified references."""

    ctx: FileContext
    snapshot: int | None


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
        p.add_includes(*type_includes(self._prim))
        p.print(_primitive_write(self._prim, var) + "\n")

    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None:
        p.add_includes("<expected>", *type_includes(self._prim))
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
        return qualified_at(self._enum.name, self._gc.ctx, self._gc.snapshot)

    def generate_serialize(self, p: Printer, var: str, depth: int = 0) -> None:
        if self._enum.scalar is None:
            p.add_includes("<bedrock/serializer.hpp>")
            p.print(f"Serializer<{self._qualified()}>::serialize(stream, {var});\n")
        else:
            p.add_includes(*type_includes(self._enum.scalar))
            p.print(_primitive_write(self._enum.scalar, var) + "\n")

    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None:
        p.add_includes("<expected>")
        if self._enum.scalar is None:
            p.add_includes("<bedrock/serializer.hpp>")
            p.print(f"auto v = Serializer<{self._qualified()}>::deserialize(stream);\n")
            p.print("if (!v) return std::unexpected(v.error());\n")
            p.print(f"{target} = *v;\n")
        else:
            p.add_includes(*type_includes(self._enum.scalar))
            p.print(_primitive_read(self._enum.scalar) + "\n")
            p.print("if (!v) return std::unexpected(v.error());\n")
            p.print(f"{target} = static_cast<{self._qualified()}>(*v);\n")


class ClassFieldGenerator(FieldGenerator):
    def __init__(self, struct_type: StructType, gc: GenContext) -> None:
        self._struct = struct_type
        self._gc = gc

    def _qualified(self) -> str:
        return qualified_at(self._struct.name, self._gc.ctx, self._gc.snapshot)

    def generate_serialize(self, p: Printer, var: str, depth: int = 0) -> None:
        p.add_includes("<bedrock/serializer.hpp>")
        p.print(f"Serializer<{self._qualified()}>::serialize(stream, {var});\n")

    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None:
        p.add_includes("<bedrock/serializer.hpp>", "<expected>")
        p.print(f"auto v = Serializer<{self._qualified()}>::deserialize(stream);\n")
        p.print("if (!v) return std::unexpected(v.error());\n")
        p.print(f"{target} = *v;\n")


class OptionalFieldGenerator(FieldGenerator):
    def __init__(self, inner: FieldGenerator, gc: GenContext) -> None:
        self._inner = inner
        self._gc = gc

    def generate_serialize(self, p: Printer, var: str, depth: int = 0) -> None:
        p.print(f"stream.write<bool>({var}.has_value());\n")
        with p.block(f"if ({var}.has_value())"):
            self._inner.generate_serialize(p, f"*{var}", depth)

    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None:
        p.add_includes("<expected>")
        p.print("auto present = stream.read<bool>();\n")
        p.print("if (!present) return std::unexpected(present.error());\n")
        with p.block("if (*present)"):
            self._inner.generate_deserialize(p, target, depth)


class RepeatedFieldGenerator(FieldGenerator):
    def __init__(self, inner: FieldGenerator, prefix: PrimitiveType, gc: GenContext) -> None:
        self._inner = inner
        self._prefix = prefix
        self._gc = gc

    def generate_serialize(self, p: Printer, var: str, depth: int = 0) -> None:
        p.add_includes(*type_includes(self._prefix))
        p.print(_primitive_write(self._prefix, f"{var}.size()") + "\n")
        with p.block(f"for (const auto &e{depth} : {var})"):
            self._inner.generate_serialize(p, f"e{depth}", depth + 1)

    def generate_deserialize(self, p: Printer, target: str, depth: int = 0) -> None:
        p.add_includes("<expected>", *type_includes(self._prefix))
        p.print(f"auto len{depth} = stream.{_read_verb(self._prefix)}();\n")
        p.print(f"if (!len{depth}) return std::unexpected(len{depth}.error());\n")
        p.print(f"{target}.clear();\n")
        with p.block(f"for (auto rep{depth} = *len{depth}; rep{depth} > 0; --rep{depth})"):
            p.print(f"{target}.emplace_back();\n")
            self._inner.generate_deserialize(p, f"{target}.back()", depth + 1)


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


def make_field_generator(t: FieldType, gc: GenContext) -> FieldGenerator:
    """`FieldGeneratorMap` factory: build the codec generator for a wire node."""
    if isinstance(t, PrimitiveType):
        return PrimitiveFieldGenerator(t, gc)
    if isinstance(t, EnumType):
        return EnumFieldGenerator(t, gc)
    if isinstance(t, StructType):
        return ClassFieldGenerator(t, gc)
    if isinstance(t, OptionalType):
        return OptionalFieldGenerator(make_field_generator(t.inner, gc), gc)
    if isinstance(t, RepeatedType):
        return RepeatedFieldGenerator(make_field_generator(t.inner, gc), t.prefix, gc)
    if isinstance(t, VariantType):
        cases = [None if c is None else make_field_generator(c, gc) for c in t.cases]
        variant_type = cpp_type(t, gc.ctx, gc.snapshot)
        assert variant_type is not None
        return VariantFieldGenerator(cases, t.discriminator, variant_type, gc)
    raise CompilerError(f"no field generator for {t!r}")
