from bedrock_protocol_compiler.descriptor import Alias, Builtin, Enum, MemberRef, Range, Struct
from bedrock_protocol_compiler.schema import Encoding, EnumType, Schema, SerializationMode, StructModel

INCLUDE_DIR = "bedrock/protocol"
REGISTRY_HEADER = f"{INCLUDE_DIR}/packets.hpp"
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
ENCODED = "std::expected<void, Errc>"


def namespace(schema: Schema) -> str:
    return schema.package.replace(".", "::")


def scope(schema: Schema, target: StructModel | EnumType) -> tuple[str, ...]:
    since = schema.scope(target)
    return () if since is None else (f"v{since}",)


def declared(schema: Schema, target: StructModel | EnumType) -> str:
    return schema.name(target) if isinstance(target, StructModel) else target.family.name


def qualified(schema: Schema, target: StructModel | EnumType | Alias | Builtin) -> str:
    if isinstance(target, Alias | Builtin):
        return f"::{namespace(schema)}::{target.name}"
    owner = schema.owner(target)
    if owner is not None:
        return f"{nested(qualified(schema, owner))}::{declared(schema, target)}"
    return "::".join(("", namespace(schema), *scope(schema, target), declared(schema, target)))


def nested(spelled: str) -> str:
    return f"{spelled}_nested"


def selector(label: str) -> str:
    return f"{label}_"


def since(schema: Schema, enum_type: EnumType) -> int:
    first = schema.enum_runs(enum_type)[0].since
    return schema.versions[0] if first is None else first


def serializer(spelled: str, version: int | str, mode: SerializationMode = SerializationMode.DEFAULT) -> str:
    suffix = "" if mode is SerializationMode.DEFAULT else f", SerializationMode::{mode.name.capitalize()}"
    return f"Serializer<{spelled}, {version}{suffix}>"


def decoded(spelled: str) -> str:
    return f"std::expected<{spelled}, Errc>"


def fail(error: str, where: str) -> str:
    return f"return stream.fail({error}, {where});"


def unexpected(error: str) -> str:
    return f"return std::unexpected({error});"


def write(encoded: str, endian: str | None, value: str) -> str:
    if encoded in ("str", "bytes"):
        return f"stream.write({value});"
    if encoded in VARINTS:
        return f"stream.writeVarInt<{PRIMITIVES[encoded]}>({value});"
    order = ", std::endian::big" if endian else ""
    return f"stream.write<{PRIMITIVES[encoded]}{order}>({value});"


def read(encoded: str, endian: str | None) -> str:
    if encoded in VARINTS:
        return f"stream.readVarInt<{PRIMITIVES[encoded]}>()"
    order = ", std::endian::big" if endian else ""
    return f"stream.read<{PRIMITIVES[encoded]}{order}>()"


def enumerator(schema: Schema, member: MemberRef, encoding: Encoding) -> str:
    enum_type = schema.enum_type(member.enum, encoding.since)
    cpp_name = next(
        (each.cpp_name for each in enum_type.members if each.name == member.name and not each.deprecated), None
    )
    if cpp_name is None:
        return f"static_cast<{qualified(schema, enum_type)}>({schema.number(encoding, member)})"
    return f"{qualified(schema, enum_type)}::{cpp_name}"


def bare(schema: Schema, target: StructModel | EnumType) -> str:
    owner = schema.owner(target)
    name = declared(schema, target)
    return name if owner is None else f"{bare(schema, owner)}::{name}"


def requirement(run: Range) -> str:
    bounds = []
    if run.since is not None:
        bounds.append(f"V >= {run.since}")
    if run.until is not None:
        bounds.append(f"V < {run.until}")
    return f" requires ({' && '.join(bounds)})" if bounds else ""


def runtime(stem: str) -> str:
    return f"<{INCLUDE_DIR}/{stem}.hpp>"


def generated(stem: str) -> str:
    return f"<{INCLUDE_DIR}/{stem}.h>"


SERIALIZER_INCLUDES = frozenset({runtime("serializer"), runtime("stream"), "<expected>"})


def header(family: Struct | Enum | Alias | Builtin) -> str:
    return runtime(family.stem) if isinstance(family, Builtin) else generated(family.module)
