"""C++ naming + spelling helpers — protoc analog of `compiler/cpp/cpp_helpers.{h,cc}`."""

from __future__ import annotations

from bedrock_protocol.descriptor import split_scope

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


#: Compiler builtin -> the hand-written header defining it and its `Serializer`.
#: The DSL names these through `BUILTIN_ANNOTATIONS`; this is the C++ mapping.
BUILTIN_HEADERS: dict[str, str] = {"UUID": "<bedrock/uuid.hpp>"}


def snapshot_namespace(version: int) -> str:
    return "base" if version == 0 else f"v{version}"


def cpp_name(declared: str) -> str:
    """A declared type's C++ spelling. A nested type is dotted in the IR
    (`Owner.Inner`) and scope-resolved in C++ (`Owner::Inner`)."""
    return declared.replace(".", "::")


def cpp_qualified(declared: str, snapshot: int | None = None) -> str:
    """A declared type's spelling from file-namespace scope:
    `[legacy::][vN::]Owner::Inner`.

    The flavour scope sits outside the snapshot rather than inside it. A
    `legacy::` written from within `vN` would find the enclosing namespace
    itself if the nesting went the other way, and bind the wrong type."""
    scope, rest = split_scope(declared)
    parts = [scope] if scope is not None else []
    if snapshot is not None:
        parts.append(snapshot_namespace(snapshot))
    parts.append(cpp_name(rest))
    return "::".join(parts)


def bare_name(declared: str) -> str:
    """A declared type's own spelling, unqualified by its flavour scope -- what
    the definition inside that scope's namespace prints."""
    return cpp_name(split_scope(declared)[1])


def outermost(declared: str) -> str:
    """The module-scope type a (possibly nested) name belongs to -- the only
    level versioning, topological order and cross-file includes work at."""
    return declared.split(".", 1)[0]


def requires_clause(lo: int, hi: int | None) -> str:
    parts: list[str] = []
    if lo:
        parts.append(f"V >= {lo}")
    if hi is not None:
        parts.append(f"V < {hi}")
    return " && ".join(parts)
