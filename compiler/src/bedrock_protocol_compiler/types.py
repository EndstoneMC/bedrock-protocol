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
    nested_enum_names: set[str] = frozenset(),
    type_aliases: set[str] = frozenset(),
) -> str | None:
    """Map a griffe annotation Expr to a bare C++ type name. None if unmappable.

    Every user-defined type resolves to its bare name. A generated type lives
    either in a version-snapshot namespace (`bedrock::protocol::v{N}`) or, when
    it never varies, directly in `bedrock::protocol`. A field declaration is
    emitted inside the snapshot namespace it belongs to, so unqualified lookup
    binds each referenced name to the right definition -- the codegen does not
    spell the namespace here.

    Module-scope and nested enums are true `enum class` types, so an enum
    reference is just the enum name: no `::Value`, no `_<ProtocolVersion>`.
    """
    if (
        isinstance(ann, griffe.ExprBinOp)
        and ann.operator == "|"
        and (ann.right == "None" or ann.left == "None")
    ):
        other = ann.left if ann.right == "None" else ann.right
        inner = resolve_type(
            other, class_names, enum_names, nested_enum_names, type_aliases
        )
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
            resolved = resolve_type(
                member, class_names, enum_names, nested_enum_names, type_aliases
            )
            if resolved is None:
                return None
            parts.append(resolved)
        return f"std::variant<{', '.join(parts)}>"
    if isinstance(ann, griffe.ExprName):
        name = ann.name
        if name in nested_enum_names:
            return name
        if name in enum_names:
            return name
        if name in class_names:
            return name
        if name in type_aliases:
            return name
        if name in PRIMITIVE_TYPES:
            return PRIMITIVE_TYPES[name]
    return None
