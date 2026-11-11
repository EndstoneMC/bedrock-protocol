from bedrock_protocol_compiler.descriptor import Alias, Builtin, Enum, Range, Struct
from bedrock_protocol_compiler.schema import Schema, Shape

INCLUDE_DIR = "bedrock/protocol"
PRIMITIVES = {
    "str": "std::string",
    "bytes": "std::vector<std::byte>",
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


def namespace(schema: Schema) -> str:
    return schema.package.replace(".", "::")


def scope(shape: Shape) -> tuple[str, ...]:
    parts = [] if shape.family.cereal else ["legacy"]
    if shape.versioned:
        since = shape.ranges[0].since
        parts.append("base" if since is None else f"v{since}")
    return tuple(parts)


def qualified(schema: Schema, target: Shape | Alias | Builtin) -> str:
    if isinstance(target, Alias | Builtin):
        return f"::{namespace(schema)}::{target.name}"
    if target.owner is not None:
        return f"{qualified(schema, target.owner)}_nested::{target.family.name}"
    return "::".join(("", namespace(schema), *scope(target), target.family.name))


def bare(family: Struct | Enum) -> str:
    return family.name if family.owner is None else f"{bare(family.owner)}::{family.name}"


def clause(run: Range) -> str:
    bounds = []
    if run.since is not None:
        bounds.append(f"V >= {run.since}")
    if run.until is not None:
        bounds.append(f"V < {run.until}")
    return " && ".join(bounds)


def runtime(stem: str) -> str:
    return f"<{INCLUDE_DIR}/{stem}.hpp>"


def generated(stem: str) -> str:
    return f"<{INCLUDE_DIR}/{stem}.h>"


def header(family: Struct | Enum | Alias | Builtin) -> str:
    return runtime(family.stem) if isinstance(family, Builtin) else generated(family.module)
