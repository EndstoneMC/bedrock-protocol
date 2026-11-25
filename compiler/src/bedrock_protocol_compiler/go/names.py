from bedrock_protocol_compiler.builder import UUID
from bedrock_protocol_compiler.descriptor import Builtin, CompilerError
from bedrock_protocol_compiler.java.names import pascal
from bedrock_protocol_compiler.schema import EnumModel, Schema, StructModel

STREAM = "stream"
LIBRARIES = {"maps": "maps", "slices": "slices", "strconv": "strconv"}
METHODS = {"str": "String", "float": "Float", "double": "Double"}
RUNTIME = (
    "Packet",
    "Pinned",
    "DecodeError",
    "EncodeError",
    "Bitset",
    "formatPath",
    "readBitset",
    "writeBitset",
    "numberOf",
    "choose",
    "failure",
    "bitsetOf",
    "casePackets",
    "caseObject",
    "caseEntry",
    "caseClass",
    "caseString",
    "caseBytes",
    "caseFloat32",
    "caseFloat64",
    "caseNumber",
    "caseName",
    "caseList",
    "caseMap",
    "caseBitset",
)


def method(encoded: str, endian: str | None = None) -> str:
    return METHODS.get(encoded, pascal(encoded)) + ("BE" if endian else "")


def module(schema: Schema) -> str:
    return schema.go_package.rpartition("/")[0]


def package(schema: Schema) -> str:
    return schema.go_package.rpartition("/")[2]


def stem(builtin: Builtin) -> str:
    return builtin.stem.replace("_", "")


def imports(schema: Schema) -> dict[str, str]:
    found = {**LIBRARIES, STREAM: f"{module(schema)}/{STREAM}"}
    builtins = [UUID]
    for source in schema.modules:
        builtins += [family for family in source.families if isinstance(family, Builtin)]
    for builtin in builtins:
        spelled = f"{module(schema)}/{stem(builtin)}"
        if found.setdefault(stem(builtin), spelled) != spelled:
            raise CompilerError(f"{spelled}: has the package name of {found[stem(builtin)]}")
    return found


def declared(schema: Schema, each: StructModel | EnumModel) -> str:
    owner = schema.owner(each)
    if owner is not None:
        return f"{declared(schema, owner)}_{each.family.name}"
    name = schema.name(each) if isinstance(each, StructModel) else each.family.name
    scope = schema.scope(each)
    return name if scope is None else f"{name}_v{scope}"


def home(schema: Schema, each: StructModel | EnumModel) -> str:
    owner = schema.owner(each)
    return each.family.module if owner is None else home(schema, owner)


def unexported(name: str) -> str:
    return name[:1].lower() + name[1:]


def path(schema: Schema, stem_name: str) -> str:
    return f"{package(schema)}/{stem_name}.bpc.go"


def test_path(schema: Schema, stem_name: str) -> str:
    return f"{package(schema)}/{stem_name}.bpc_test.go"
