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


#: Directory every emitted header is included through, matching the install tree.
INCLUDE_PREFIX = "bedrock/protocol"

#: Compiler builtin -> the hand-written header defining it and its `Serializer`.
#: The DSL names these through `BUILTIN_ANNOTATIONS`; this is the C++ mapping.
BUILTIN_HEADERS: dict[str, str] = {"UUID": f"<{INCLUDE_PREFIX}/uuid.hpp>"}


def snapshot_namespace(version: int) -> str:
    return "base" if version == 0 else f"v{version}"


def cpp_name(declared: str) -> str:
    """A declared type's C++ spelling. A nested type is dotted in the IR
    (`Owner.Inner`) and scope-resolved in C++ (`Owner::Inner`)."""
    return declared.replace(".", "::")


def cpp_qualified(
    declared: str,
    snapshot: int | None = None,
    *,
    owner: str | None = None,
    package: str | None = None,
) -> str:
    """A declared type's spelling as written from inside `owner`'s namespace
    tree: `[legacy::][vN::]Owner::Inner`.

    The pre-cereal tree is `legacy::vN`, so both trees hold a namespace named
    `vN`. A reference out of the pre-cereal tree into a versioned cerealised
    type therefore anchors at `package`: spelled `vN::` it would find
    `legacy::vN` first and bind the wrong type. Within one tree, and for an
    unversioned type in either, the relative spelling is unambiguous."""
    scope, rest = split_scope(declared)
    parts: list[str] = []
    if scope == owner:
        pass  # same tree; unqualified lookup walks out to it
    elif scope is not None:
        parts.append(scope)
    elif snapshot is not None and package:
        parts.append(package.replace(".", "::"))
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
