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


type Type = Primitive | AliasRef | StructRef | BuiltinRef


@dataclass(frozen=True)
class Field:
    name: str
    type: Type


@dataclass(frozen=True)
class StructDeclaration:
    fields: tuple[Field, ...]


@dataclass(eq=False)
class Struct:
    name: str
    owner: "Struct | None"
    module: str
    packet_id: int | None
    declarations: list[StructDeclaration] = field(default_factory=list)
    nested: list["Struct"] = field(default_factory=list)


@dataclass(eq=False)
class Alias:
    name: str
    module: str
    primitive: Primitive = field(init=False)


@dataclass(eq=False)
class Builtin:
    name: str
    stem: str


type Family = Struct | Alias | Builtin


@dataclass(frozen=True)
class Module:
    stem: str
    package: str
    families: tuple[Family, ...]


@dataclass(frozen=True)
class Package:
    versions: tuple[int, ...]
    modules: tuple[Module, ...]
