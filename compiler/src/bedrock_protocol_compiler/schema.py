import dataclasses
from collections.abc import Iterator
from dataclasses import dataclass, field, replace

from bedrock_protocol_compiler.descriptor import (
    Binary,
    CompilerError,
    Enum,
    Field,
    Int,
    Member,
    MemberRef,
    Package,
    Primitive,
    Range,
    Struct,
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
    underlying: Primitive | None
    members: tuple[Member, ...]
    ranges: list[Range] = field(default_factory=list)
    owner: StructShape | None = None
    versioned: bool = True


type Shape = StructShape | EnumShape


def reaches(node: object) -> Iterator[Struct | Enum]:
    if isinstance(node, Struct | Enum):
        yield node
    elif isinstance(node, tuple | list):
        for item in node:
            yield from reaches(item)
    elif dataclasses.is_dataclass(node):
        for each in dataclasses.fields(node):
            yield from reaches(getattr(node, each.name))


class Schema:
    def __init__(self, package: Package) -> None:
        self.versions = package.versions
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

    def shapes(self, family: Struct | Enum) -> list[Shape]:
        return self.family_shapes[family]

    def shape_at(self, family: Struct | Enum, version: int) -> Shape:
        return self.live[family, version]

    def place(self, family: Struct | Enum, placed: set[Struct | Enum]) -> None:
        if family in placed:
            return
        placed.add(family)
        if isinstance(family, Struct):
            for dependency in reaches([[declaration.fields for declaration in family.declarations], family.nested]):
                self.place(dependency, placed)
        self.order.append(family)

    def project(self, family: Struct | Enum) -> None:
        shapes: dict[tuple[object, ...], Shape] = {}
        versions_of: dict[Shape, list[int]] = {}
        for version in self.versions:
            if not any(each.range.contains(version) for each in family.declarations):
                continue
            if isinstance(family, Struct):
                struct_declaration = next(each for each in family.declarations if each.range.contains(version))
                present = tuple(
                    replace(each, range=ALWAYS) for each in struct_declaration.fields if each.range.contains(version)
                )
                nested = tuple(
                    self.shape_at(child, version)
                    for child in family.nested
                    if any(each.range.contains(version) for each in child.declarations)
                )
                reached = tuple(self.shape_at(each, version) for each in dict.fromkeys(reaches(present)))
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
                    reference: str | None = None
                    offset = 0
                    match member.value:
                        case None:
                            number += 1
                        case Int(value=literal):
                            number = literal
                        case MemberRef(name=reference):
                            pass
                        case Binary(left=MemberRef(name=reference), right=Int(value=offset)):
                            pass
                    if reference is not None:
                        if reference not in numbers:
                            raise CompilerError(
                                f"{family.name}.{member.name}: names {reference}, which does not exist at {version}"
                            )
                        number = numbers[reference] - offset
                    numbers[member.name] = number
                    members.append(replace(member, value=Int(number), range=ALWAYS))
                key = (enum_declaration.underlying, tuple(members))
                candidate = EnumShape(family, enum_declaration.underlying, tuple(members))
            shape = shapes.setdefault(key, candidate)
            versions_of.setdefault(shape, []).append(version)
        for shape, live in versions_of.items():
            positions = [self.versions.index(version) for version in live]
            start = 0
            for stop in range(1, len(positions) + 1):
                if stop < len(positions) and positions[stop] == positions[stop - 1] + 1:
                    continue
                first = positions[start]
                last = positions[stop - 1]
                since = None if first == 0 else self.versions[first]
                until = None if last == len(self.versions) - 1 else self.versions[last + 1]
                shape.ranges.append(Range(since, until))
                start = stop
            for version in live:
                self.live[family, version] = shape
            shape.versioned = len(shapes) > 1 or shape.ranges != [ALWAYS]
            if isinstance(shape, StructShape):
                for child in shape.nested:
                    if child.owner is None:
                        child.owner = shape
        self.family_shapes[family] = list(shapes.values())
