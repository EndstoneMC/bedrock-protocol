"""Mapping from Python type annotations to C++ types."""

import griffe

PRIMITIVE_TYPES = {
    "str": "std::string",
    "int": "int",
    "bool": "bool",
    "float32": "float",
    "float64": "double",
    "varint32": "std::int32_t",
    "varint64": "std::int64_t",
    "uvarint32": "std::uint32_t",
    "uvarint64": "std::uint64_t",
    "int8": "std::int8_t",
    "int16": "std::int16_t",
    "int32": "std::int32_t",
    "int32be": "std::int32_t",
    "int64": "std::int64_t",
    "uint8": "std::uint8_t",
    "uint16": "std::uint16_t",
    "uint32": "std::uint32_t",
    "uint64": "std::uint64_t",
}


WIRE_METHODS = {
    "bool":      {"write": "writeBool",                "read": "getBool",                "underlying": "bool"},
    "int8":      {"write": "writeByte",                "read": "getByte",                "underlying": "std::uint8_t"},
    "uint8":     {"write": "writeByte",                "read": "getByte",                "underlying": "std::uint8_t"},
    "int16":     {"write": "writeSignedShort",         "read": "getSignedShort",         "underlying": "std::int16_t"},
    "uint16":    {"write": "writeUnsignedShort",       "read": "getUnsignedShort",       "underlying": "std::uint16_t"},
    "int32":     {"write": "writeSignedInt",           "read": "getSignedInt",           "underlying": "std::int32_t"},
    "uint32":    {"write": "writeUnsignedInt",         "read": "getUnsignedInt",         "underlying": "std::uint32_t"},
    "int32be":   {"write": "writeSignedBigEndianInt",  "read": "getSignedBigEndianInt",  "underlying": "std::int32_t"},
    "int64":     {"write": "writeSignedInt64",         "read": "getSignedInt64",         "underlying": "std::int64_t"},
    "uint64":    {"write": "writeUnsignedInt64",       "read": "getUnsignedInt64",       "underlying": "std::uint64_t"},
    "varint32":  {"write": "writeVarInt",              "read": "getVarInt",              "underlying": "std::int32_t"},
    "varint64":  {"write": "writeVarInt64",            "read": "getVarInt64",            "underlying": "std::int64_t"},
    "uvarint32": {"write": "writeUnsignedVarInt",      "read": "getUnsignedVarInt",      "underlying": "std::uint32_t"},
    "uvarint64": {"write": "writeUnsignedVarInt64",    "read": "getUnsignedVarInt64",    "underlying": "std::uint64_t"},
    "float32":   {"write": "writeFloat",               "read": "getFloat",               "underlying": "float"},
    "float64":   {"write": "writeDouble",              "read": "getDouble",              "underlying": "double"},
}


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
