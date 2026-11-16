import re

from bedrock_protocol_compiler.builder import UUID
from bedrock_protocol_compiler.descriptor import Builtin, CompilerError
from bedrock_protocol_compiler.schema import Encoding, EnumModel, Schema, SerializationMode, StructModel

LIBRARIES = {
    "ArrayList": "java.util.ArrayList",
    "Arrays": "java.util.Arrays",
    "BitSet": "java.util.BitSet",
    "Collections": "java.util.Collections",
    "Comparator": "java.util.Comparator",
    "List": "java.util.List",
    "Locale": "java.util.Locale",
    "Map": "java.util.Map",
    "Objects": "java.util.Objects",
    "Optional": "java.util.Optional",
    "SortedMap": "java.util.SortedMap",
    "TreeMap": "java.util.TreeMap",
    "ByteBuf": "io.netty.buffer.ByteBuf",
    "NotNull": "org.jetbrains.annotations.NotNull",
    "Nullable": "org.jetbrains.annotations.Nullable",
}
MODE = "SerializationMode"
RUNTIME = ("ByteBufCodec", "Codec", "DecodeException", "Decoder", "Message", "Packet", "PacketHeader", MODE)
JAVA_LANG = (
    "Boolean",
    "Deprecated",
    "Double",
    "Float",
    "IllegalArgumentException",
    "IllegalStateException",
    "Integer",
    "Iterable",
    "Long",
    "Object",
    "Override",
    "String",
)
OBJECT_METHODS = (
    ("clone", 0),
    ("equals", 1),
    ("finalize", 0),
    ("getClass", 0),
    ("hashCode", 0),
    ("notify", 0),
    ("notifyAll", 0),
    ("toString", 0),
    ("wait", 0),
    ("wait", 1),
    ("wait", 2),
)
OBJECT = "java.lang.Object"
BUILDER = "Builder"
REGISTRY = "Packets"
VERSION = "ProtocolVersion"
INTERNAL = "internal"
CODEC = "Codec"
ATOM = re.compile(r"[\w.]+(?:\([^()]*\))?")


def runtime(schema: Schema, name: str) -> str:
    return f"{schema.java_package}.{name}"


def imports(schema: Schema) -> dict[str, str]:
    found = {**LIBRARIES, **{name: runtime(schema, name) for name in RUNTIME}}
    builtins = [UUID] + [each for module in schema.modules for each in module.families if isinstance(each, Builtin)]
    for builtin in builtins:
        stem = builtin.stem.replace("_", "")
        spelled = "java.util.UUID" if builtin is UUID else f"{schema.java_package}.{stem}.{builtin.name}"
        if found.setdefault(builtin.name, spelled) != spelled:
            raise CompilerError(f"{spelled}: has the simple name of {found[builtin.name]}")
    return found


def reserved(schema: Schema) -> frozenset[str]:
    return frozenset(imports(schema)) | frozenset(JAVA_LANG)


def package(schema: Schema, each: StructModel | EnumModel) -> str:
    scope = schema.scope(each)
    return schema.java_package if scope is None else f"{schema.java_package}.v{scope}"


def declared(schema: Schema, each: StructModel | EnumModel) -> str:
    return schema.name(each) if isinstance(each, StructModel) else each.family.name


def qualified(schema: Schema, each: StructModel | EnumModel) -> str:
    owner = schema.owner(each)
    if owner is not None:
        return f"{qualified(schema, owner)}.{each.family.name}"
    return f"{package(schema, each)}.{declared(schema, each)}"


def internal(schema: Schema) -> str:
    return f"{schema.java_package}.{INTERNAL}"


def nested(schema: Schema, each: StructModel | EnumModel) -> str:
    owner = schema.owner(each)
    return declared(schema, each) if owner is None else f"{nested(schema, owner)}.{each.family.name}"


def numbering(schema: Schema, each: EnumModel) -> str:
    return f"{nested(schema, each).replace('.', '')}Numbering"


def bounds(since: int | None, until: int | None, variable: str = "version") -> list[str]:
    found = []
    if since is not None:
        found.append(f"{variable} >= {since}")
    if until is not None:
        found.append(f"{variable} < {until}")
    return found


def codec(encoding: Encoding) -> str:
    suffix = "" if encoding.mode is SerializationMode.DEFAULT else pascal(encoding.mode.name.lower())
    return f"{CODEC}{encoding.since}{suffix}"


def registry(schema: Schema, version: int) -> str:
    return f"{schema.java_package}.v{version}"


def path(package_name: str, name: str) -> str:
    return f"{package_name.replace('.', '/')}/{name}.java"


def pascal(snake: str) -> str:
    spelled: list[str] = []
    upper = True
    for char in snake:
        if char == "_":
            upper = True
            continue
        spelled.append(char.upper() if upper else char)
        upper = char.isdigit()
    return "".join(spelled)


def camel(snake: str) -> str:
    spelled = pascal(snake)
    return spelled[:1].lower() + spelled[1:]


def snake(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()


def atom(code: str) -> str:
    return code if ATOM.fullmatch(code) else f"({code})"
