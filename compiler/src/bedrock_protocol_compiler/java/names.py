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
    "HashMap": "java.util.HashMap",
    "List": "java.util.List",
    "Locale": "java.util.Locale",
    "Map": "java.util.Map",
    "Objects": "java.util.Objects",
    "Optional": "java.util.Optional",
    "SortedMap": "java.util.SortedMap",
    "TreeMap": "java.util.TreeMap",
    "ByteBuf": "io.netty.buffer.ByteBuf",
    "ByteBufUtil": "io.netty.buffer.ByteBufUtil",
    "Unpooled": "io.netty.buffer.Unpooled",
    "NotNull": "org.jetbrains.annotations.NotNull",
    "Nullable": "org.jetbrains.annotations.Nullable",
}
MODE = "SerializationMode"
RUNTIME = ("ByteBufCodec", "Codec", "DecodeException", "Decoder", "Message", "Packet")
JAVA_LANG = (
    "Boolean",
    "Class",
    "Deprecated",
    "Double",
    "Float",
    "IllegalArgumentException",
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
VERSION = "ProtocolVersion"
PROTOCOL = "Protocol"
INTERNAL = "internal"
CODEC = "Codec"
ATOM = re.compile(r"[\w.]+(?:\([^()]*\))?")


def runtime(schema: Schema, name: str) -> str:
    return f"{schema.java_package}.{name}"


def imports(schema: Schema) -> dict[str, str]:
    found = {**LIBRARIES, **{name: runtime(schema, name) for name in RUNTIME}, MODE: f"{internal(schema)}.{MODE}"}
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


def home(schema: Schema, each: StructModel | EnumModel) -> str:
    owner = schema.owner(each)
    return package(schema, each) if owner is None else home(schema, owner)


def declared(schema: Schema, each: StructModel | EnumModel) -> str:
    name = schema.name(each) if isinstance(each, StructModel) else each.family.name
    if schema.owner(each) is not None:
        return name
    scope = schema.scope(each)
    return name if scope is None else f"{name}_v{scope}"


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


def bounded(schema: Schema, since: int | None, until: int | None) -> list[str]:
    lowest = schema.versions[0] if since is None else since
    if until is None and lowest == schema.latest:
        return [f"version == {lowest}"]
    return [f"version >= {lowest}", f"version <= {schema.latest}" if until is None else f"version < {until}"]


def suffix(encoding: Encoding) -> str:
    mode = "" if encoding.mode is SerializationMode.DEFAULT else pascal(encoding.mode.name.lower())
    excluded = "" if encoding.excluded is None else f"Exclude{pascal(encoding.excluded)}"
    return f"{encoding.since}{mode}{excluded}"


def codec(encoding: Encoding) -> str:
    return f"{CODEC}{suffix(encoding)}"


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
