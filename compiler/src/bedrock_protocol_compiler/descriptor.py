from dataclasses import dataclass, field


class CompilerError(Exception):
    pass


@dataclass(frozen=True)
class Primitive:
    name: str
    wire: str | None = None
    endian: str | None = None


@dataclass(frozen=True)
class AliasRef:
    alias: "Alias"
    wire: str | None = None


@dataclass(frozen=True)
class StructRef:
    struct: "Struct"


@dataclass(frozen=True)
class BuiltinRef:
    builtin: "Builtin"


@dataclass(frozen=True)
class EnumRef:
    enum: "Enum"
    wire: str | None = None
    endian: str | None = None


@dataclass(frozen=True)
class EnumName:
    enum: "Enum"


@dataclass(frozen=True)
class Optional:
    element: "Type"


@dataclass(frozen=True)
class List:
    element: "Type"
    prefix: Primitive | None
    count: "Expression | None" = None


@dataclass(frozen=True)
class Array:
    element: "Type"
    size: int


@dataclass(frozen=True)
class Map:
    key: "Type"
    value: "Type"


@dataclass(frozen=True)
class Variant:
    cases: tuple["Type | None", ...]


@dataclass(frozen=True)
class Literal:
    value: "bool | str | MemberRef"


@dataclass(frozen=True)
class Bitset:
    width: "MemberRef"


type Type = (
    Primitive
    | AliasRef
    | StructRef
    | BuiltinRef
    | EnumRef
    | EnumName
    | Optional
    | List
    | Array
    | Map
    | Variant
    | Literal
    | Bitset
)


@dataclass(frozen=True)
class Range:
    since: int | None
    until: int | None

    def contains(self, version: int) -> bool:
        return (self.since is None or self.since <= version) and (self.until is None or version < self.until)

    def overlaps(self, other: "Range") -> bool:
        return (self.since is None or other.until is None or self.since < other.until) and (
            other.since is None or self.until is None or other.since < self.until
        )

    def intersect(self, other: "Range") -> "Range":
        bounds = [bound for bound in (self.since, other.since) if bound is not None]
        ends = [end for end in (self.until, other.until) if end is not None]
        return Range(max(bounds, default=None), min(ends, default=None))


@dataclass(frozen=True)
class Field:
    name: str
    type: Type
    range: Range
    when: "Expression | None" = None


@dataclass(frozen=True)
class StructDeclaration:
    range: Range
    fields: tuple[Field, ...]


@dataclass(frozen=True)
class Int:
    value: int


@dataclass(frozen=True)
class MemberRef:
    enum: "Enum"
    name: str


@dataclass(frozen=True)
class FieldRef:
    name: str


@dataclass(frozen=True)
class Len:
    field: str


@dataclass(frozen=True)
class Test:
    field: str
    member: MemberRef


@dataclass(frozen=True)
class Not:
    operand: "Expression"


@dataclass(frozen=True)
class Binary:
    operator: str
    left: "Expression"
    right: "Expression"


type Expression = FieldRef | MemberRef | Int | Len | Test | Not | Binary


@dataclass(frozen=True)
class Member:
    name: str
    value: Int | MemberRef | Binary | None
    range: Range
    cpp_name: str
    wire_name: str


@dataclass(frozen=True)
class EnumDeclaration:
    range: Range
    underlying: Primitive | None
    members: tuple[Member, ...]


@dataclass(eq=False)
class Struct:
    name: str
    owner: "Struct | None"
    module: str
    cereal: bool
    packet_id: int | None
    declarations: list[StructDeclaration] = field(default_factory=list)
    nested: list["Struct | Enum"] = field(default_factory=list)


@dataclass(eq=False)
class Enum:
    name: str
    owner: Struct | None
    module: str
    cereal: bool
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
