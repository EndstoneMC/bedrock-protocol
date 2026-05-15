"""Mapping from Python type annotations to C++ types."""

import griffe

PRIMITIVE_TYPES = {
    "str": "std::string",
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


# Subset of PRIMITIVE_TYPES that map to a varint wire encoding. The codegen
# uses this to choose between `stream.write<T, true>(v)` (varint) and
# `stream.write<T>(v)` (fixed-width little-endian) when emitting Serializer
# bodies — no per-primitive method-name table is needed.
VARINT_PRIMITIVES = {"varint32", "varint64", "uvarint32", "uvarint64"}


def resolve_type(
    ann,
    class_names: set[str],
    enum_names: set[str],
    templated_classes: set[str] = frozenset(),
    type_aliases: set[str] = frozenset(),
) -> str | None:
    """Map a griffe annotation Expr to a C++ type. None if unmappable.

    `templated_classes` is the subset of `class_names` that are emitted as
    class templates (`Foo_<V>`). The complement (plain POD-ish structs)
    is referenced by its bare name. Enums are always templated. Aliases
    (`type X = primitive`) emit as `enum X : T {}` at namespace scope and
    are referenced by their bare name.
    """
    if (
        isinstance(ann, griffe.ExprBinOp)
        and ann.operator == "|"
        and (ann.right == "None" or ann.left == "None")
    ):
        other = ann.left if ann.right == "None" else ann.right
        inner = resolve_type(other, class_names, enum_names, templated_classes, type_aliases)
        if inner is None:
            return None
        return f"std::optional<{inner}>"
    if (
        isinstance(ann, griffe.ExprSubscript)
        and isinstance(ann.left, griffe.ExprName)
        and ann.left.name == "Union"
    ):
        elements = (
            ann.slice.elements
            if isinstance(ann.slice, griffe.ExprTuple)
            else [ann.slice]
        )
        parts: list[str] = []
        for member in elements:
            if isinstance(member, str) and member == "None":
                parts.append("std::monostate")
                continue
            resolved = resolve_type(member, class_names, enum_names, templated_classes, type_aliases)
            if resolved is None:
                return None
            parts.append(resolved)
        return f"std::variant<{', '.join(parts)}>"
    if isinstance(ann, griffe.ExprName):
        name = ann.name
        if name in enum_names:
            return f"{name}_<ProtocolVersion>::Value"
        if name in class_names:
            if name in templated_classes:
                return f"{name}_<ProtocolVersion>"
            return name
        if name in type_aliases:
            return name
        if name in PRIMITIVE_TYPES:
            return PRIMITIVE_TYPES[name]
    return None
