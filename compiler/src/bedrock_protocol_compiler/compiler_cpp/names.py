"""C++ naming + spelling helpers."""

from __future__ import annotations

import inflection

#: DSL primitive name → C++ type spelling.
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


def snapshot_namespace(version: int) -> str:
    return "base" if version == 0 else f"v{version}"


def camel(name: str) -> str:
    return inflection.camelize(name.lower())


def requires_clause(lo: int, hi: int | None) -> str:
    parts: list[str] = []
    if lo:
        parts.append(f"V >= {lo}")
    if hi is not None:
        parts.append(f"V < {hi}")
    return " && ".join(parts)
