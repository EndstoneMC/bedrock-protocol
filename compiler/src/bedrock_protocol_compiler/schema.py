from collections.abc import Collection, Iterator
from dataclasses import dataclass, field, replace

from bedrock_protocol_compiler.builder import WIDTHS, reaches
from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    Array,
    Binary,
    Bitset,
    BuiltinRef,
    CompilerError,
    Enum,
    EnumName,
    EnumRef,
    Expression,
    Field,
    Int,
    List,
    Literal,
    Map,
    Member,
    MemberRef,
    Not,
    Optional,
    Package,
    Primitive,
    Range,
    Struct,
    StructRef,
    Test,
    Type,
    Variant,
)

ALWAYS = Range(None, None)
DOMAINS = {name: f"{'' if signed else 'u'}int{width}" for name, (signed, width) in WIDTHS.items() if width > 1}
HIGHEST = {name: (1 << (width - signed)) - 1 for name, (signed, width) in WIDTHS.items()}


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


@dataclass(frozen=True)
class Slot:
    name: str
    type: Type


@dataclass(eq=False)
class StructModel:
    family: Struct
    slots: tuple[Slot, ...]
    nested: tuple["Model", ...]
    runs: dict[Struct, list[Range]] = field(default_factory=dict)
    owner: "StructModel | None" = None
    since: int | None = None
    versioned: bool = True


@dataclass(eq=False)
class EnumModel:
    family: Enum
    underlying: Primitive
    members: tuple[Member, ...]
    values: dict[str, int]
    runs: dict[Enum, list[Range]] = field(default_factory=dict)
    owner: StructModel | None = None
    since: int | None = None
    versioned: bool = True


type Model = StructModel | EnumModel


@dataclass(eq=False)
class Encoding:
    model: StructModel
    fields: tuple[Field, ...]
    reached: dict[StructRef | EnumRef | EnumName, "Encoding | Numbering | Naming"]
    numbers: dict[MemberRef, int]
    runs: dict[Struct, list[Range]] = field(default_factory=dict)
    since: int = field(init=False)
    cereal: bool = False


@dataclass(eq=False)
class Numbering:
    model: EnumModel
    moved: dict[int, int]
    identity: bool
    runs: list[Range] = field(default_factory=list)
    since: int = field(init=False)


@dataclass(eq=False)
class Naming:
    model: EnumModel
    names: dict[str, str]
    written: dict[int, str]
    runs: list[Range] = field(default_factory=list)
    since: int = field(init=False)


def strip(node: Type) -> Type:
    match node:
        case Primitive(name=name):
            return Primitive(DOMAINS.get(name, name))
        case AliasRef(alias=alias):
            return AliasRef(alias)
        case BuiltinRef(builtin=builtin):
            return BuiltinRef(builtin)
        case EnumRef(enum=enum) | EnumName(enum=enum):
            return EnumRef(enum)
        case Optional(element=element):
            return Optional(strip(element))
        case List(element=element):
            return List(strip(element), None)
        case Array(element=element, size=size):
            return Array(strip(element), size)
        case Map(key=key, value=value):
            return Map(strip(key), strip(value))
        case Variant(cases=cases):
            return Variant(tuple(None if case is None else strip(case) for case in cases))
    return node


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


def qualified(family: Struct | Enum) -> str:
    return family.name if family.owner is None else f"{qualified(family.owner)}.{family.name}"


def numbered_by(node: Type | Expression | None) -> Iterator[MemberRef]:
    match node:
        case MemberRef():
            yield node
        case Literal(value=MemberRef() as member) | Test(member=member):
            yield member
        case Optional(element=element) | List(element=element) | Array(element=element):
            yield from numbered_by(element)
        case Not(operand=operand):
            yield from numbered_by(operand)
        case Binary(left=left, right=right) | Map(key=left, value=right):
            yield from numbered_by(left)
            yield from numbered_by(right)
        case Variant(cases=cases):
            for case in cases:
                yield from numbered_by(case)


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
        self.struct_models: dict[tuple[Struct, int], StructModel] = {}
        self.enum_models: dict[tuple[Enum, int], EnumModel] = {}
        self.encoded: dict[tuple[Struct, int], Encoding] = {}
        self.numbered: dict[tuple[Enum, int], Numbering] = {}
        self.named: dict[tuple[Enum, int], Naming] = {}
        self.numbers: dict[tuple[Enum, int], dict[str, int]] = {}
        self.family_models: dict[Struct | Enum, list[Model]] = {}
        self.model_encodings: dict[StructModel, list[Encoding]] = {}
        self.read_at: dict[StructModel, int] = {}
        struct_forms: dict[Struct, list[Struct]] = {}
        enum_forms: dict[Enum, list[Enum]] = {}
        for family in sorted(self.order, key=lambda family: not family.cereal):
            if isinstance(family, Struct):
                struct_forms.setdefault(self.pair(family), []).append(family)
            else:
                enum_forms.setdefault(self.pair(family), []).append(family)
        for enums in enum_forms.values():
            self.project_enum(enums)
        models: dict[tuple[object, ...], StructModel] = {}
        encodings: dict[tuple[object, ...], Encoding] = {}
        for family in self.order:
            if isinstance(family, Struct):
                self.project_struct(family, models, encodings)
        spans: dict[StructModel | Encoding, dict[Struct, list[int]]] = {}
        for forms in struct_forms.values():
            held: list[StructModel] = []
            for form in forms:
                for version in self.versions:
                    if (form, version) not in self.struct_models:
                        continue
                    model = self.struct_models[form, version]
                    encoding = self.encoded[form, version]
                    if model not in held:
                        held.append(model)
                    if encoding not in self.model_encodings.setdefault(model, []):
                        self.model_encodings[model].append(encoding)
                    if self.read_at.setdefault(model, version) < version:
                        self.read_at[model] = version
                    for each in (model, encoding):
                        spans.setdefault(each, {}).setdefault(form, []).append(version)
            for form in forms:
                self.family_models[form] = [*held]
            for model in held:
                for child in model.nested:
                    if child.owner is None:
                        child.owner = model
                read = self.read_at[model]
                holder = next(self.live[form, read] for form in forms if self.struct_models.get((form, read)) is model)
                if isinstance(holder, StructShape):
                    model.slots = tuple(
                        Slot(each.name, strip(each.type))
                        for each in holder.fields
                        if not isinstance(each.type, Literal)
                    )
        for each, found in spans.items():
            each.runs = {family: self.ranges(versions) for family, versions in found.items()}
            if isinstance(each, Encoding):
                each.since = min(min(versions) for versions in found.values())
                each.cereal = any(family.cereal for family in found)
            else:
                primary = next(iter(each.runs.values()))
                each.since = primary[0].since
                each.versioned = primary != [ALWAYS]

    def models(self, family: Struct | Enum) -> list[Model]:
        return self.family_models[family]

    def model_at(self, family: Struct | Enum, version: int) -> Model:
        if isinstance(family, Struct):
            return self.struct_models[family, version]
        return self.enum_models[family, version]

    def encodings(self, model: StructModel) -> list[Encoding]:
        return self.model_encodings[model]

    def encoding_at(self, family: Struct, version: int) -> Encoding:
        return self.encoded[family, version]

    def numbering_at(self, enum: Enum, version: int) -> Numbering:
        return self.numbered[enum, version]

    def naming_at(self, enum: Enum, version: int) -> Naming:
        return self.named[enum, version]

    def numbers_at(self, enum: Enum, version: int) -> dict[str, int]:
        return self.numbers[enum, version]

    def target(self, model: StructModel, node: StructRef | EnumRef) -> Model:
        return self.model_at(node.struct if isinstance(node, StructRef) else node.enum, self.read_at[model])

    def width(self, model: StructModel, node: Bitset) -> int:
        return self.numbers[node.width.enum, self.read_at[model]][node.width.name]

    def number(self, encoding: Encoding, member: MemberRef) -> int:
        return encoding.numbers[member]

    def packets(self, version: int) -> dict[int, Encoding]:
        return {
            family.packet_id: self.encoded[family, version]
            for family in self.order
            if isinstance(family, Struct) and family.packet_id is not None and (family, version) in self.encoded
        }

    def pair[F: (Struct, Enum)](self, family: F) -> F:
        if family.cereal:
            return family
        if family.owner is None:
            return next(
                each
                for each in self.order
                if isinstance(each, type(family)) and each.cereal and each.owner is None and each.name == family.name
            )
        return next(
            (
                each
                for each in self.pair(family.owner).nested
                if isinstance(each, type(family)) and each.name == family.name
            ),
            family,
        )

    def coded(
        self,
        node: Type | Expression | None,
        version: int,
        reached: dict[StructRef | EnumRef | EnumName, "Encoding | Numbering | Naming"],
    ) -> object:
        match node:
            case StructRef(struct=family):
                return reached.setdefault(node, self.encoded[family, version])
            case EnumRef(enum=family, encoded=encoded, endian=endian):
                return reached.setdefault(node, self.numbered[family, version]), encoded, endian
            case EnumName(enum=family):
                return reached.setdefault(node, self.named[family, version])
            case MemberRef(enum=family, name=name):
                return self.model_at(family, version), name, self.numbers[family, version][name]
            case Literal(value=MemberRef(enum=family) as member):
                shape = self.live[family, version]
                if not isinstance(shape, EnumShape):
                    raise CompilerError(f"{family.module}.py: {qualified(family)}: is not an enum at {version}")
                return Literal, shape.underlying, self.coded(member, version, reached)
            case Bitset(width=member):
                return Bitset, self.coded(member, version, reached)
            case Test(field=tested, member=member):
                return Test, tested, self.coded(member, version, reached)
            case Optional(element=element):
                return Optional, self.coded(element, version, reached)
            case List(element=element, prefix=prefix, count=count):
                return List, self.coded(element, version, reached), prefix, self.coded(count, version, reached)
            case Array(element=element, size=size):
                return Array, size, self.coded(element, version, reached)
            case Map(key=key, value=value):
                return Map, self.coded(key, version, reached), self.coded(value, version, reached)
            case Variant(cases=cases):
                return Variant, tuple(self.coded(case, version, reached) for case in cases)
            case Not(operand=operand):
                return Not, self.coded(operand, version, reached)
            case Binary(operator=operator, left=left, right=right):
                return Binary, operator, self.coded(left, version, reached), self.coded(right, version, reached)
        return node

    def ranges(self, versions: Collection[int]) -> list[Range]:
        runs: list[Range] = []
        previous = False
        for version in self.versions:
            if (version in versions) != previous:
                if previous:
                    runs[-1] = Range(runs[-1].since, version)
                else:
                    runs.append(Range(None if version == self.versions[0] else version, None))
            previous = version in versions
        return runs

    def resolved(self, node: Type | None, version: int) -> object:
        match node:
            case StructRef(struct=family) | EnumRef(enum=family):
                return self.model_at(family, version)
            case Bitset(width=width):
                return self.numbers[width.enum, version][width.name]
            case Optional(element=element) | List(element=element):
                return type(node), self.resolved(element, version)
            case Array(element=element, size=size):
                return Array, size, self.resolved(element, version)
            case Map(key=key, value=value):
                return Map, self.resolved(key, version), self.resolved(value, version)
            case Variant(cases=cases):
                return Variant, tuple(self.resolved(case, version) for case in cases)
        return node

    def project_enum(self, forms: list[Enum]) -> None:
        family = forms[0]
        underlying = family.declarations[-1].underlying
        order: dict[str, None] = {}
        for form in forms:
            for declaration in reversed(form.declarations):
                for member in declaration.members:
                    if not member.sentinel:
                        order.setdefault(member.name)
        newest: dict[str, Member] = {}
        for version in reversed(self.versions):
            for form in forms:
                shape = self.live.get((form, version))
                if isinstance(shape, EnumShape):
                    for member in shape.members:
                        newest.setdefault(member.name, member)
        derived = {name for name, member in newest.items() if isinstance(member.value, MemberRef | Binary)}
        values: dict[str, int] = {}
        firsts: dict[str, int] = {}
        seen: set[int] = set()
        for version in self.versions:
            for form in forms:
                shape = self.live.get((form, version))
                if not isinstance(shape, EnumShape):
                    continue
                seen.update(shape.numbers.values())
                for member in shape.members:
                    firsts.setdefault(member.name, shape.numbers[member.name])
                    if member.name in values or member.name in derived:
                        continue
                    number = shape.numbers[member.name]
                    if any(
                        values.get(other.name) == number and shape.numbers[other.name] != number
                        for other in shape.members
                    ):
                        number = max(seen) + 1
                        if number > HIGHEST[underlying.name]:
                            raise CompilerError(
                                f"{form.module}.py: {qualified(form)}.{member.name}: has no library value above "
                                f"{number - 1} that fits {underlying.name}"
                            )
                    values[member.name] = number
                    seen.add(number)
        for name in order:
            match newest[name].value:
                case MemberRef(name=other) | Binary(left=MemberRef(name=other)) if other not in values:
                    values[name] = firsts[name]
                case MemberRef(name=other):
                    values[name] = values[other]
                case Binary(left=MemberRef(name=other), right=Int(value=offset)):
                    values[name] = values[other] - offset
        model = EnumModel(
            family,
            underlying,
            tuple(
                newest[name] if name in derived else replace(newest[name], value=Int(values[name])) for name in order
            ),
            {name: values[name] for name in order},
        )
        numberings: dict[tuple[object, ...], Numbering] = {}
        namings: dict[tuple[frozenset[tuple[str, str]], frozenset[tuple[int, str]]], Naming] = {}
        spans: dict[Numbering | Naming, set[int]] = {}
        for form in forms:
            self.family_models[form] = [model]
            for version in self.versions:
                shape = self.live.get((form, version))
                if not isinstance(shape, EnumShape):
                    continue
                self.enum_models[form, version] = model
                self.numbers[form, version] = shape.numbers
                pairs = [
                    (values[member.name], shape.numbers[member.name])
                    for member in shape.members
                    if member.name not in derived
                ]
                mapped = dict(pairs)
                if len(set(pairs)) != len(mapped) or len(set(mapped.values())) != len(mapped):
                    raise CompilerError(
                        f"{form.module}.py: {qualified(form)}: does not number its library values one to one at "
                        f"{version}"
                    )
                displaced = sorted(set(mapped.values()) - mapped.keys())
                freed = sorted(mapped.keys() - set(mapped.values()))
                moved = {value: number for value, number in mapped.items() if value != number} | dict(
                    zip(displaced, freed, strict=True)
                )
                numbering = numberings.setdefault(
                    (shape.underlying, tuple(sorted(moved.items()))), Numbering(model, moved, not moved)
                )
                self.numbered[form, version] = numbering
                spans.setdefault(numbering, set()).add(version)
                if form in self.name_coded:
                    canonical: dict[int, str] = {}
                    for member in sorted(
                        shape.members, key=lambda member: not isinstance(member.value, MemberRef | Binary)
                    ):
                        canonical.setdefault(shape.numbers[member.name], member.encoded_name)
                    names = {member.name: member.encoded_name for member in shape.members}
                    written = {value: canonical[number] for value, number in mapped.items()}
                    naming = namings.setdefault(
                        (frozenset(names.items()), frozenset(written.items())), Naming(model, names, written)
                    )
                    self.named[form, version] = naming
                    spans.setdefault(naming, set()).add(version)
            model.runs[form] = self.ranges([version for version in self.versions if (form, version) in self.live])
        for coding, versions in spans.items():
            coding.runs = self.ranges(versions)
            coding.since = min(versions)
        primary = next(iter(model.runs.values()))
        model.since = primary[0].since
        model.versioned = primary != [ALWAYS]

    def project_struct(
        self,
        family: Struct,
        models: dict[tuple[object, ...], StructModel],
        encodings: dict[tuple[object, ...], Encoding],
    ) -> None:
        pair = self.pair(family)
        for version in self.versions:
            shape = self.live.get((family, version))
            if not isinstance(shape, StructShape):
                continue
            nested = tuple(self.model_at(child, version) for child in family.nested if (child, version) in self.live)
            slots = frozenset(
                (each.name, self.resolved(strip(each.type), version))
                for each in shape.fields
                if not isinstance(each.type, Literal)
            )
            model = models.setdefault((pair, slots, nested), StructModel(pair, (), nested))
            self.struct_models[family, version] = model
            reached: dict[StructRef | EnumRef | EnumName, Encoding | Numbering | Naming] = {}
            coding = tuple(
                (
                    each.name,
                    self.coded(each.type, version, reached),
                    self.coded(each.when, version, reached),
                    each.duplicate,
                )
                for each in shape.fields
            )
            numbers = {
                member: self.numbers[member.enum, version][member.name]
                for each in shape.fields
                for member in (*numbered_by(each.type), *numbered_by(each.when))
            }
            self.encoded[family, version] = encodings.setdefault(
                (model, coding), Encoding(model, shape.fields, reached, numbers)
            )

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
                    if member.sentinel:
                        continue
                    settled = replace(member, range=ALWAYS)
                    if not isinstance(member.value, MemberRef | Binary):
                        settled = replace(settled, value=Int(number))
                    members.append(settled)
                key = (enum_declaration.underlying, tuple(members), tuple(numbers.items()))
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
