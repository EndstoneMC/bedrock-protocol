import re

from bedrock_protocol_compiler.builder import UUID
from bedrock_protocol_compiler.descriptor import Builtin, CompilerError
from bedrock_protocol_compiler.schema import Schema, Shape, StructShape

LIBRARIES = {
    "ArrayList": "java.util.ArrayList",
    "Arrays": "java.util.Arrays",
    "BitSet": "java.util.BitSet",
    "Collections": "java.util.Collections",
    "Comparator": "java.util.Comparator",
    "List": "java.util.List",
    "Map": "java.util.Map",
    "Objects": "java.util.Objects",
    "Optional": "java.util.Optional",
    "SortedMap": "java.util.SortedMap",
    "TreeMap": "java.util.TreeMap",
    "ByteBuf": "io.netty.buffer.ByteBuf",
    "NotNull": "org.jetbrains.annotations.NotNull",
    "Nullable": "org.jetbrains.annotations.Nullable",
}
RUNTIME = ("ByteBufCodec", "DecodeException", "Decoder", "Message", "Packet", "PacketHeader")
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
PRE_CEREAL = "precereal"
BASE = "base"
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


def host(schema: Schema, shape: Shape) -> StructShape | None:
    owner = shape.family.owner
    if owner is None:
        return None
    listing = [each for each in schema.shapes(owner) if isinstance(each, StructShape) and shape in each.nested]
    if not listing:
        raise CompilerError(f"{shape.family.name}: no shape of {owner.name} nests it")
    return max(
        listing,
        key=lambda each: max(version for version in schema.versions if schema.live.get((owner, version)) is each),
    )


def package(schema: Schema, shape: Shape) -> str:
    parts = [] if shape.family.cereal else [PRE_CEREAL]
    if schema.live.get((shape.family, schema.latest)) is not shape:
        since = shape.ranges[0].since
        parts.append(BASE if since is None else f"v{since}")
    return ".".join((schema.java_package, *parts))


def qualified(schema: Schema, shape: Shape) -> str:
    owner = host(schema, shape)
    if owner is not None:
        return f"{qualified(schema, owner)}.{shape.family.name}"
    return f"{package(schema, shape)}.{shape.family.name}"


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
