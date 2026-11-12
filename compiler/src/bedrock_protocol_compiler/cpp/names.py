from bedrock_protocol_compiler.descriptor import Alias, Builtin, Enum, MemberRef, Range, Struct
from bedrock_protocol_compiler.schema import EnumShape, Schema, Shape

INCLUDE_DIR = "bedrock/protocol"
PRE_CEREAL = "pre_cereal"
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
VARINTS = ("varint32", "varint64", "uvarint32", "uvarint64")
OUT_OF_RANGE = "Errc::out_of_range"
UNKNOWN_VALUE = "Errc::unknown_value"


def namespace(schema: Schema) -> str:
    return schema.package.replace(".", "::")


def scope(shape: Shape) -> tuple[str, ...]:
    parts = [] if shape.family.cereal else [PRE_CEREAL]
    if shape.versioned:
        since = shape.ranges[0].since
        parts.append("base" if since is None else f"v{since}")
    return tuple(parts)


def qualified(schema: Schema, target: Shape | Alias | Builtin) -> str:
    if isinstance(target, Alias | Builtin):
        return f"::{namespace(schema)}::{target.name}"
    if target.owner is not None:
        return f"{nested(qualified(schema, target.owner))}::{target.family.name}"
    return "::".join(("", namespace(schema), *scope(target), target.family.name))


def nested(spelled: str) -> str:
    return f"{spelled}_nested"


def selector(family: Struct | Enum) -> str:
    return f"{family.name}_"


def decoded(spelled: str) -> str:
    return f"std::expected<{spelled}, Errc>"


def fail(error: str, where: str) -> str:
    return f"return stream.fail({error}, {where});"


def unexpected(error: str) -> str:
    return f"return std::unexpected({error});"


def write(wire: str, endian: str | None, value: str) -> str:
    if wire in ("str", "bytes"):
        return f"stream.write({value});"
    if wire in VARINTS:
        return f"stream.writeVarInt<{PRIMITIVES[wire]}>({value});"
    order = ", std::endian::big" if endian else ""
    return f"stream.write<{PRIMITIVES[wire]}{order}>({value});"


def account(count: str, container: str) -> str:
    return f"stream.account({count}, sizeof({container}::value_type))"


def read(wire: str, endian: str | None) -> str:
    if wire in VARINTS:
        return f"stream.readVarInt<{PRIMITIVES[wire]}>()"
    order = ", std::endian::big" if endian else ""
    return f"stream.read<{PRIMITIVES[wire]}{order}>()"


def enumerator(schema: Schema, member: MemberRef, version: int) -> str:
    shape = schema.shape_at(member.enum, version)
    assert isinstance(shape, EnumShape)
    cpp_name = next(each.cpp_name for each in shape.members if each.name == member.name)
    return f"{qualified(schema, shape)}::{cpp_name}"


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


SERIALIZER_INCLUDES = frozenset({runtime("serializer"), runtime("stream"), "<expected>"})


def header(family: Struct | Enum | Alias | Builtin) -> str:
    return runtime(family.stem) if isinstance(family, Builtin) else generated(family.module)
