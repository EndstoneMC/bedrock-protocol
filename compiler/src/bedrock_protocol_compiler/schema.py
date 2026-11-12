from collections.abc import Iterator
from dataclasses import dataclass, field, replace

from bedrock_protocol_compiler.builder import reaches
from bedrock_protocol_compiler.descriptor import (
    Binary,
    Enum,
    EnumName,
    Field,
    Int,
    List,
    Map,
    Member,
    MemberRef,
    Optional,
    Package,
    Primitive,
    Range,
    Struct,
    Type,
)

ALWAYS = Range(None, None)


@dataclass(eq=False)
class StructShape:
    family: Struct
    fields: tuple[Field, ...]
    nested: tuple["Shape", ...]
    ranges: list[Range] = field(default_factory=list)
    owner: "StructShape | None" = None
    versioned: bool = True


@dataclass(eq=False)
class EnumShape:
    family: Enum
    underlying: Primitive
    members: tuple[Member, ...]
    numbers: dict[str, int]
    ranges: list[Range] = field(default_factory=list)
    owner: StructShape | None = None
    versioned: bool = True


type Shape = StructShape | EnumShape


def name_coded(node: Type) -> Iterator[Enum]:
    match node:
        case EnumName(enum=enum):
            yield enum
        case Optional(element=element) | List(element=element):
            yield from name_coded(element)
        case Map(key=key, value=value):
            yield from name_coded(key)
            yield from name_coded(value)


def outermost(family: Struct | Enum) -> Struct | Enum:
    return family if family.owner is None else outermost(family.owner)


def roots_reached(family: Struct | Enum) -> set[Struct | Enum]:
    reached: set[Struct | Enum] = set()
    if isinstance(family, Struct):
        for declaration in family.declarations:
            for each in declaration.fields:
                reached.update(outermost(target) for target in reached_by(each))
        for child in family.nested:
            reached |= roots_reached(child)
    return reached - {family}


def reached_by(each: Field) -> Iterator[Struct | Enum]:
    for target in (*reaches(each.type), *reaches(each.when)):
        yield target.enum if isinstance(target, MemberRef) else target


class Schema:
    def __init__(self, package: Package) -> None:
        self.modules = package.modules
        self.package = package.modules[0].package
        self.java_package = package.modules[0].java_package
        self.versions = package.versions
        self.releases = package.releases
        self.latest = package.versions[-1]
        self.order: list[Struct | Enum] = []
        self.family_shapes: dict[Struct | Enum, list[Shape]] = {}
        self.live: dict[tuple[Struct | Enum, int], Shape] = {}
        placed: set[Struct | Enum] = set()
        for module in package.modules:
            for family in module.families:
                if isinstance(family, Struct | Enum):
                    self.place(family, placed)
        for family in self.order:
            self.project(family)
        self.name_coded = {
            enum
            for family in self.order
            if isinstance(family, Struct)
            for declaration in family.declarations
            for each in declaration.fields
            for enum in name_coded(each.type)
        }

    def shapes(self, family: Struct | Enum) -> list[Shape]:
        return self.family_shapes[family]

    def shape_at(self, family: Struct | Enum, version: int) -> Shape:
        return self.live[family, version]

    def place(self, family: Struct | Enum, placed: set[Struct | Enum]) -> None:
        if family in placed:
            return
        placed.add(family)
        if isinstance(family, Struct):
            for declaration in family.declarations:
                for each in declaration.fields:
                    for target in reached_by(each):
                        self.place(target, placed)
            for child in family.nested:
                self.place(child, placed)
        self.order.append(family)

    def project(self, family: Struct | Enum) -> None:
        shapes: dict[tuple[object, ...], Shape] = {}
        for version in self.versions:
            if not any(each.range.contains(version) for each in family.declarations):
                continue
            if isinstance(family, Struct):
                struct_declaration = next(each for each in family.declarations if each.range.contains(version))
                present = tuple(
                    replace(each, range=ALWAYS) for each in struct_declaration.fields if each.range.contains(version)
                )
                nested = tuple(self.live[child, version] for child in family.nested if (child, version) in self.live)
                reached = tuple(self.shape_at(target, version) for each in present for target in reached_by(each))
                key: tuple[object, ...] = (present, nested, reached)
                candidate: Shape = StructShape(family, present, nested)
            else:
                enum_declaration = next(each for each in family.declarations if each.range.contains(version))
                members: list[Member] = []
                numbers: dict[str, int] = {}
                number = -1
                for member in enum_declaration.members:
                    if not member.range.contains(version):
                        continue
                    match member.value:
                        case None:
                            number += 1
                        case Int(value=literal):
                            number = literal
                        case MemberRef(name=name):
                            number = numbers[name]
                        case Binary(left=MemberRef(name=name), right=Int(value=offset)):
                            number = numbers[name] - offset
                    numbers[member.name] = number
                    settled = replace(member, range=ALWAYS)
                    if not isinstance(member.value, MemberRef | Binary):
                        settled = replace(settled, value=Int(number))
                    members.append(settled)
                key = (enum_declaration.underlying, tuple(members))
                candidate = EnumShape(family, enum_declaration.underlying, tuple(members), numbers)
            self.live[family, version] = shapes.setdefault(key, candidate)
        previous: Shape | None = None
        for version in self.versions:
            current = self.live.get((family, version))
            if current is not previous:
                if previous is not None:
                    previous.ranges[-1] = Range(previous.ranges[-1].since, version)
                if current is not None:
                    current.ranges.append(Range(None if version == self.versions[0] else version, None))
            previous = current
        for shape in shapes.values():
            shape.versioned = shape.ranges != [ALWAYS]
            if isinstance(shape, StructShape):
                for child in shape.nested:
                    if child.owner is None:
                        child.owner = shape
        self.family_shapes[family] = list(shapes.values())
