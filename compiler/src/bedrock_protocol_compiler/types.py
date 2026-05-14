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
}


def resolve_type(ann, class_names: set[str], enum_names: set[str]) -> str | None:
    """Map a griffe annotation Expr to a C++ type. None if unmappable.

    Routes user-defined classes through their `ProtocolVersion` template, uses
    the inner `::Value` enum type for IntEnum classes, and maps explicit
    `Union[A, B, None]` to `std::variant<A, B, std::monostate>`.
    """
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
