"""Mapping from Python type annotations to C++ types."""

import griffe

PRIMITIVE_TYPES = {
    "str": "std::string",
    "int": "int",
    "bool": "bool",
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


# Wire-encoding name → (BinaryStream write method, ReadOnlyBinaryStream read
# method, underlying C++ integer the serializer converts to/from). Used by the
# generated Serializer specializations. Fixed-width entries embed the type as
# a template argument in the method name so the codegen call site stays
# uniform. Little-endian is the default; big-endian variants would be named
# explicitly (e.g. writeIntBE) when needed.
WIRE_METHODS = {
    "uvarint32": {
        "write": "writeUnsignedVarInt",
        "read": "getUnsignedVarInt",
        "underlying": "std::uint32_t",
    },
    "varint32": {
        "write": "writeVarInt",
        "read": "getVarInt",
        "underlying": "std::int32_t",
    },
    "int8":   {"write": "writeInt<std::int8_t>",   "read": "getInt<std::int8_t>",   "underlying": "std::int8_t"},
    "int16":  {"write": "writeInt<std::int16_t>",  "read": "getInt<std::int16_t>",  "underlying": "std::int16_t"},
    "int32":  {"write": "writeInt<std::int32_t>",  "read": "getInt<std::int32_t>",  "underlying": "std::int32_t"},
    "int64":  {"write": "writeInt<std::int64_t>",  "read": "getInt<std::int64_t>",  "underlying": "std::int64_t"},
    "uint8":  {"write": "writeInt<std::uint8_t>",  "read": "getInt<std::uint8_t>",  "underlying": "std::uint8_t"},
    "uint16": {"write": "writeInt<std::uint16_t>", "read": "getInt<std::uint16_t>", "underlying": "std::uint16_t"},
    "uint32": {"write": "writeInt<std::uint32_t>", "read": "getInt<std::uint32_t>", "underlying": "std::uint32_t"},
    "uint64": {"write": "writeInt<std::uint64_t>", "read": "getInt<std::uint64_t>", "underlying": "std::uint64_t"},
}


def resolve_type(ann, class_names: set[str], enum_names: set[str]) -> str | None:
    """Map a griffe annotation Expr to a C++ type. None if unmappable.

    Routes user-defined classes through their `ProtocolVersion` template, uses
    the inner `::Value` enum type for IntEnum classes, maps `X | None` to
    `std::optional<X>`, and maps explicit `Union[A, B, None]` to
    `std::variant<A, B, std::monostate>` (for true multi-way unions).
    """
    if (
        isinstance(ann, griffe.ExprBinOp)
        and ann.operator == "|"
        and (ann.right == "None" or ann.left == "None")
    ):
        other = ann.left if ann.right == "None" else ann.right
        inner = resolve_type(other, class_names, enum_names)
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
            resolved = resolve_type(member, class_names, enum_names)
            if resolved is None:
                return None
            parts.append(resolved)
        return f"std::variant<{', '.join(parts)}>"
    if isinstance(ann, griffe.ExprName):
        name = ann.name
        if name in enum_names:
            return f"{name}<ProtocolVersion>::Value"
        if name in class_names:
            return f"{name}<ProtocolVersion>"
        if name in PRIMITIVE_TYPES:
            return PRIMITIVE_TYPES[name]
    return None
