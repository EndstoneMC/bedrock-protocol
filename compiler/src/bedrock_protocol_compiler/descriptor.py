from dataclasses import dataclass, field


class CompilerError(Exception):
    pass


@dataclass(frozen=True)
class Primitive:
    name: str


@dataclass(frozen=True)
class AliasRef:
    alias: "Alias"


@dataclass(frozen=True)
class StructRef:
    struct: "Struct"


@dataclass(frozen=True)
class BuiltinRef:
    builtin: "Builtin"


@dataclass(frozen=True)
class EnumRef:
    enum: "Enum"


type Type = Primitive | AliasRef | StructRef | BuiltinRef | EnumRef


@dataclass(frozen=True)
class Field:
    name: str
    type: Type


@dataclass(frozen=True)
class StructDeclaration:
    fields: tuple[Field, ...]


@dataclass(frozen=True)
class Range:
    since: int | None
    until: int | None


@dataclass(frozen=True)
class Int:
    value: int


@dataclass(frozen=True)
class MemberRef:
    enum: "Enum"
    name: str


@dataclass(frozen=True)
class Binary:
    operator: str
    left: MemberRef
    right: Int


@dataclass(frozen=True)
class Member:
    name: str
    value: Int | MemberRef | Binary | None
    range: Range
    cpp_name: str | None
    wire_name: str | None


@dataclass(frozen=True)
class EnumDeclaration:
    underlying: Primitive | None
    members: tuple[Member, ...]


@dataclass(eq=False)
class Struct:
    name: str
    owner: "Struct | None"
    module: str
    packet_id: int | None
    declarations: list[StructDeclaration] = field(default_factory=list)
    nested: list["Struct | Enum"] = field(default_factory=list)


@dataclass(eq=False)
class Enum:
    name: str
    owner: Struct | None
    module: str
    declarations: list[EnumDeclaration] = field(default_factory=list)


@dataclass(eq=False)
class Alias:
    name: str
    module: str
    primitive: Primitive = field(init=False)


@dataclass(eq=False)
class Builtin:
    name: str
    stem: str


type Family = Struct | Enum | Alias | Builtin


@dataclass(frozen=True)
class Module:
    stem: str
    package: str
    families: tuple[Family, ...]


@dataclass(frozen=True)
class Package:
    versions: tuple[int, ...]
    modules: tuple[Module, ...]
