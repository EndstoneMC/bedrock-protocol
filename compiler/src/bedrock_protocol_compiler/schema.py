from collections.abc import Collection, Iterator, Sequence
from dataclasses import dataclass, field, replace
from enum import IntEnum
from typing import cast

from bedrock_protocol_compiler.builder import WIDTHS, reaches
from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    Array,
    Binary,
    Bitset,
    Choice,
    Color,
    CompilerError,
    Enum,
    EnumName,
    EnumRef,
    Expression,
    Field,
    FieldRef,
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
CEREALIZED = "Cerealized"
DOMAINS = {name: f"{'' if signed else 'u'}int{width}" for name, (signed, width) in WIDTHS.items() if width > 1}
HIGHEST = {name: (1 << (width - signed)) - 1 for name, (signed, width) in WIDTHS.items()}


class SerializationMode(IntEnum):
    DEFAULT = 0
    CEREAL = 1
    MANUAL = 2


@dataclass(eq=False)
class StructShape:
    family: Struct
    fields: tuple[Field, ...]
    nested: tuple["Shape", ...]
    manual: bool
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
    nested: tuple["StructModel | EnumType", ...]
    runs: dict[Struct, list[Range]] = field(default_factory=dict)
    versioned: bool = True


@dataclass(eq=False)
class EnumModel:
    family: Enum
    underlying: Primitive
    members: tuple[Member, ...]
    values: dict[str, int]
    derived: frozenset[str] = frozenset()
    runs: dict[Enum, list[Range]] = field(default_factory=dict)
    since: int | None = None
    versioned: bool = True


type Model = StructModel | EnumModel
type EnumType = EnumModel


@dataclass(eq=False)
class Encoding:
    model: StructModel
    fields: tuple[Field, ...]
    reached: dict[StructRef | EnumRef | EnumName, "Encoding | Numbering | Naming"]
    numbers: dict[MemberRef, int]
    runs: dict[Struct, list[Range]] = field(default_factory=dict)
    since: int = field(init=False)
    mode: SerializationMode = field(init=False)
    served: dict[SerializationMode, list[Range]] = field(default_factory=dict)
    excluded: str | None = None
    manual: bool = False


@dataclass(eq=False)
class Numbering:
    model: EnumModel
    encoded: dict[int, int]
    decoded: dict[int, int]
    absent: frozenset[int]
    lossy: frozenset[int]
    identity: bool
    runs: list[Range] = field(default_factory=list)
    since: int = field(init=False)


@dataclass(eq=False)
class Naming:
    model: EnumModel
    names: dict[str, str]
    written: dict[int, str]
    read: dict[str, int]
    runs: list[Range] = field(default_factory=list)
    since: int = field(init=False)


def strip(node: Type) -> Type:
    match node:
        case Primitive(name=name):
            return Primitive(DOMAINS.get(name, name))
        case AliasRef(alias=alias):
            return AliasRef(alias)
        case StructRef(struct=family) | Color(struct=family):
            return StructRef(family)
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


def channels(model: StructModel) -> list[str]:
    """A packed colour's member names, from the one in its highest byte."""
    *rest, highest = (slot.name for slot in model.slots)
    return [highest, *rest]


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
    for target in (*reaches(each.type), *reaches(each.when), *reaches(each.duplicate)):
        yield target.enum if isinstance(target, MemberRef) else target


def qualified(family: Struct | Enum) -> str:
    return family.name if family.owner is None else f"{qualified(family.owner)}.{family.name}"


def numbered_by(node: Type | Expression | None) -> Iterator[MemberRef]:
    match node:
        case Literal(value=MemberRef() as member) | Test(member=member) | Bitset(width=member):
            yield member
        case Optional(element=element) | List(element=element) | Array(element=element):
            yield from numbered_by(element)
        case Not(operand=operand):
            yield from numbered_by(operand)
        case Choice(test=test, when_true=when_true, when_false=when_false):
            yield from numbered_by(test)
            yield from numbered_by(when_true)
            yield from numbered_by(when_false)
        case Binary(left=left, right=right) | Map(key=left, value=right):
            yield from numbered_by(left)
            yield from numbered_by(right)
        case Variant(cases=cases):
            for case in cases:
                yield from numbered_by(case)


def operands(node: Expression | None) -> Iterator[tuple[str | None, MemberRef | FieldRef, Expression | None]]:
    match node:
        case MemberRef() | FieldRef():
            yield None, node, None
        case Not(operand=operand):
            yield from operands(operand)
        case Binary(operator=operator, left=left, right=right):
            for operand, other in ((left, right), (right, left)):
                if isinstance(operand, MemberRef | FieldRef):
                    yield operator, operand, other
                else:
                    yield from operands(operand)


class Schema:
    def __init__(self, package: Package) -> None:
        self.modules = package.modules
        self.package = package.modules[0].package
        self.java_package = package.modules[0].java_package
        self.go_package = package.modules[0].go_package
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
        self.model_numberings: dict[EnumModel, list[Numbering]] = {}
        self.model_namings: dict[EnumModel, list[Naming]] = {}
        self.numbers: dict[tuple[Enum, int], dict[str, int]] = {}
        self.merged: dict[tuple[Enum, int], tuple[str, str]] = {}
        self.family_models: dict[Struct | Enum, list[Model]] = {}
        self.model_encodings: dict[StructModel, list[Encoding]] = {}
        self.read_at: dict[StructModel, int] = {}
        self.exclusions: dict[tuple[object, ...], Encoding] = {}
        self.excluding: dict[Encoding, dict[Struct, set[int]]] = {}
        struct_forms: dict[Struct, list[Struct]] = {}
        enum_forms: dict[Enum, list[Enum]] = {}
        for family in sorted(self.order, key=lambda family: not family.cereal):
            if isinstance(family, Struct):
                struct_forms.setdefault(self.pair(family), []).append(family)
            else:
                enum_forms.setdefault(self.pair(family), []).append(family)
        pairs: list[Sequence[Struct | Enum]] = [*struct_forms.values(), *enum_forms.values()]
        self.forms = {form: tuple(forms) for forms in pairs for form in forms}
        for enums in enum_forms.values():
            self.project_enum(enums)
        models: dict[tuple[object, ...], StructModel] = {}
        encodings: dict[tuple[object, ...], Encoding] = {}
        for family in self.order:
            if isinstance(family, Struct):
                self.project_struct(family, models, encodings)
        spans: dict[StructModel | Encoding, dict[Struct, list[int]]] = {}
        served: dict[Encoding, dict[SerializationMode, list[int]]] = {}
        for forms in struct_forms.values():
            for form in forms:
                held: list[StructModel] = []
                mixed = self.mixed(form)
                for version in self.versions:
                    if (form, version) not in self.struct_models:
                        continue
                    model = self.struct_models[form, version]
                    encoding = self.encoded[form, version]
                    if model not in held:
                        held.append(model)
                    if encoding not in self.model_encodings.setdefault(model, []):
                        self.model_encodings[model].append(encoding)
                    for each in (model, encoding):
                        spans.setdefault(each, {}).setdefault(form, []).append(version)
                    mode = SerializationMode.DEFAULT
                    if any(run.contains(version) for run in mixed):
                        mode = SerializationMode.CEREAL if form.cereal else SerializationMode.MANUAL
                    served.setdefault(encoding, {}).setdefault(mode, []).append(version)
                self.family_models[form] = [*held]
        for each, found in spans.items():
            each.runs = {family: self.ranges(versions) for family, versions in found.items()}
            if isinstance(each, Encoding):
                each.since = min(min(versions) for versions in found.values())
                each.served = {mode: self.ranges(versions) for mode, versions in served[each].items()}
                each.mode = min(mode for mode, versions in served[each].items() if each.since in versions)
                continue
            read = max(max(versions) for versions in found.values())
            holder = self.live[next(form for form, versions in found.items() if read in versions), read]
            self.read_at[each] = read
            each.family = next(iter(found))
            each.versioned = self.ranges([version for versions in found.values() for version in versions]) != [ALWAYS]
            if isinstance(holder, StructShape):
                each.slots = tuple(
                    Slot(each.name, strip(each.type)) for each in holder.fields if not isinstance(each.type, Literal)
                )
        for exclusion, calls in self.excluding.items():
            exclusion.runs = {family: self.ranges(versions) for family, versions in calls.items()}
            exclusion.since = min(min(versions) for versions in calls.values())
            full = next(
                self.encoded[family, exclusion.since]
                for family, versions in calls.items()
                if exclusion.since in versions
            )
            exclusion.mode = min(
                mode for mode, runs in full.served.items() if any(run.contains(exclusion.since) for run in runs)
            )
            self.model_encodings[exclusion.model].append(exclusion)
        for model, listed in self.model_encodings.items():
            listed.sort(key=lambda encoding: encoding.since)
            for version in self.versions:
                modes = {
                    mode
                    for encoding in listed
                    for mode, runs in encoding.served.items()
                    if any(run.contains(version) for run in runs)
                }
                if SerializationMode.DEFAULT in modes and len(modes) > 1:
                    raise CompilerError(
                        f"{model.family.module}.py: {qualified(model.family)}: has the default mode and another at "
                        f"{version}"
                    )
        holders: dict[StructModel | EnumType, list[StructModel]] = {}
        for model in self.read_at:
            for child in model.nested:
                holders.setdefault(child, []).append(model)
        self.owners = {
            child: max(held, key=lambda model: (self.read_at[model], self.name(model) == model.family.name))
            for child, held in holders.items()
        }
        for family in self.order:
            if isinstance(family, Enum) and not family.cereal and family.owner is None:
                raise CompilerError(
                    f"{family.module}.py: {qualified(family)}: a cereal=False enum is declared at module scope"
                )
        reached: set[tuple[Struct | Enum, int]] = set()
        pending: list[tuple[Struct | Enum, int]] = [
            (family, version)
            for family, version in self.live
            if isinstance(family, Struct) and family.packet_id is not None
        ]
        while pending:
            key = pending.pop()
            if key in reached:
                continue
            reached.add(key)
            shape = self.live[key]
            if isinstance(shape, StructShape):
                pending.extend((target, key[1]) for each in shape.fields for target in reached_by(each))
        for family, version in self.live:
            if not family.cereal and family.owner is None and (family, version) not in reached:
                raise CompilerError(
                    f"{family.module}.py: {qualified(family)}: the hand-written form is live at {version} but no "
                    "packet reaches it"
                )
        for child, owner in self.owners.items():
            name = self.name(owner)
            if name == owner.family.name:
                continue
            runs = (
                self.enum_runs(child)
                if isinstance(child, EnumModel)
                else [run for each in child.runs.values() for run in each]
            )
            overlap = self.overlap(owner.family)
            outside = [
                version
                for version in self.versions
                if any(run.contains(version) for run in runs) and not any(run.contains(version) for run in overlap)
            ]
            if outside:
                raise CompilerError(
                    f"{child.family.module}.py: {qualified(child.family)}: is owned by {name} but is live at "
                    f"{outside[0]}, outside its overlap"
                )
        named: dict[tuple[Struct, int | None, str], StructModel] = {}
        for model in self.read_at:
            if model.family.owner is not None:
                continue
            first = self.scope(model)
            name = self.name(model)
            if named.setdefault((self.pair(model.family), first, name), model) is not model:
                raise CompilerError(
                    f"{model.family.module}.py: {qualified(model.family)}: the hand-written and the cereal form both "
                    f"hold a type named {name} " + (f"at {self.latest}" if first is None else f"from {first}")
                )

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

    def numberings(self, model: EnumModel) -> list[Numbering]:
        return self.model_numberings[model]

    def namings(self, model: EnumModel) -> list[Naming]:
        return self.model_namings[model]

    def numbers_at(self, enum: Enum, version: int) -> dict[str, int]:
        return self.numbers[enum, version]

    def enum_type(self, enum: Enum, version: int) -> EnumType:
        shape = self.live[enum, version]
        if not isinstance(shape, EnumShape):
            raise CompilerError(f"{enum.module}.py: {qualified(enum)}: is not an enum at {version}")
        return self.enum_models[enum, version]

    def enum_types(self, family: Enum) -> list[EnumType]:
        return [cast(EnumModel, self.family_models[family][0])]

    def resolve(self, member: MemberRef, version: int) -> MemberRef:
        model = self.enum_models[member.enum, version]
        if member.name not in model.derived:
            return member
        numbers = self.numbers[member.enum, version]
        shape = cast(EnumShape, self.live[member.enum, version])
        return next(
            MemberRef(member.enum, each.name)
            for each in shape.members
            if each.name not in model.derived and numbers[each.name] == numbers[member.name]
        )

    def enumerators(self, enum_type: EnumType) -> dict[str, int]:
        return enum_type.values

    def enum_runs(self, enum_type: EnumType) -> list[Range]:
        return self.ranges(
            [
                version
                for version in self.versions
                if any(run.contains(version) for runs in enum_type.runs.values() for run in runs)
            ]
        )

    def target(self, model: StructModel, node: StructRef | Color | EnumRef | EnumName) -> StructModel | EnumType:
        if isinstance(node, StructRef | Color):
            return self.struct_models[node.struct, self.read_at[model]]
        return self.enum_type(node.enum, self.read_at[model])

    def default_member(self, model: StructModel, node: EnumRef | EnumName) -> Member | None:
        shape = cast(EnumShape, self.live[node.enum, self.read_at[model]])
        return next((member for member in shape.members if member.default), None)

    def owner(self, child: StructModel | EnumType) -> StructModel | None:
        return self.owners.get(child)

    def call(self, encoding: Encoding, node: StructRef) -> tuple[int, SerializationMode]:
        child = cast(Encoding, encoding.reached[node])
        mode = SerializationMode.MANUAL
        if node.struct.cereal and any(form.cereal for form in encoding.runs):
            mode = SerializationMode.CEREAL
        if not any(run.contains(child.since) for run in child.served.get(mode, [])):
            mode = child.mode
        return child.since, mode

    def scope(self, target: StructModel | EnumType) -> int | None:
        if target.family.owner is not None:
            raise CompilerError(
                f"{target.family.module}.py: {qualified(target.family)}: is nested and is named through its owner"
            )
        runs = (
            [run for each in target.runs.values() for run in each]
            if isinstance(target, StructModel)
            else self.enum_runs(target)
        )
        if any(run.until is None for run in runs):
            return None
        return min(self.versions[0] if run.since is None else run.since for run in runs)

    def mixed(self, family: Struct | Enum) -> list[Range]:
        forms = self.forms[outermost(family)]
        if len(forms) == 1:
            return []
        return self.ranges(
            [version for version in self.versions if all((form, version) in self.live for form in forms)]
        )

    def overlap(self, family: Struct | Enum) -> list[Range]:
        forms = self.forms[outermost(family)]
        mixed = self.mixed(family)
        return self.ranges(
            [
                version
                for version in self.versions
                if any(run.contains(version) for run in mixed)
                and len({self.model_at(form, version) for form in forms}) > 1
            ]
        )

    def label(self, family: Struct | Enum, version: int) -> str:
        if family.owner is None and family.cereal and any(run.contains(version) for run in self.overlap(family)):
            return CEREALIZED + family.name
        return family.name

    def name(self, model: StructModel) -> str:
        if all(
            self.label(form, version) != form.name
            for form, runs in model.runs.items()
            for version in self.versions
            if any(run.contains(version) for run in runs)
        ):
            return CEREALIZED + model.family.name
        return model.family.name

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
            case StructRef(struct=family, excluded=excluded, args=args):
                child = self.encoded[family, version]
                kept = tuple(each for each in child.fields if each.name != excluded)
                if len(kept) < len(child.fields):
                    child = self.project_encoding(family, child.model, kept, version, self.exclusions, excluded)
                    self.excluding.setdefault(child, {}).setdefault(family, set()).add(version)
                return reached.setdefault(node, child), self.coded(args, version, reached)
            case Color(struct=family, encoded=encoded):
                return Color, self.encoded[family, version].model, encoded
            case EnumRef(enum=family, encoded=encoded, endian=endian):
                return reached.setdefault(node, self.numbered[family, version]), encoded, endian
            case EnumName(enum=family):
                return reached.setdefault(node, self.named[family, version])
            case MemberRef(enum=family):
                name = self.resolve(node, version).name
                return self.enum_models[family, version], name, self.enum_models[family, version].values.get(name)
            case Literal(value=MemberRef(enum=family, name=name)) | Bitset(width=MemberRef(enum=family, name=name)):
                return type(node), self.enum_models[family, version], name, self.numbers[family, version][name]
            case Test(field=tested, member=MemberRef(enum=family, name=name)):
                return Test, tested, self.enum_models[family, version], name, self.numbers[family, version][name]
            case Optional(element=element):
                return Optional, self.coded(element, version, reached)
            case List(element=element, prefix=prefix, count=count):
                return List, self.coded(element, version, reached), prefix, self.coded(count, version, reached)
            case Array(element=element, size=size):
                return Array, size, self.coded(element, version, reached)
            case Map(key=key, value=value):
                if isinstance(key, EnumRef | EnumName) and (key.enum, version) in self.merged:
                    derived, target = self.merged[key.enum, version]
                    raise CompilerError(
                        f"{key.enum.module}.py: {qualified(key.enum)}: keys a dict at {version}, where {derived} "
                        f"encodes to {target}'s number"
                    )
                return Map, self.coded(key, version, reached), self.coded(value, version, reached)
            case Variant(cases=cases):
                return Variant, tuple(self.coded(case, version, reached) for case in cases)
            case Not(operand=operand):
                return Not, self.coded(operand, version, reached)
            case Choice(test=test, when_true=when_true, when_false=when_false):
                return (
                    Choice,
                    self.coded(test, version, reached),
                    self.coded(when_true, version, reached),
                    self.coded(when_false, version, reached),
                )
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
            case StructRef(struct=family):
                return self.model_at(family, version)
            case EnumRef(enum=family):
                return self.enum_type(family, version)
            case Bitset(width=width):
                numbers = self.numbers[width.enum, version]
                model = self.enum_models[width.enum, version]
                for member in model.members:
                    value = model.values[member.name]
                    if member.name in model.derived:
                        continue
                    if member.name not in numbers:
                        if value < numbers[width.name]:
                            raise CompilerError(
                                f"{width.enum.module}.py: {qualified(width.enum)}: lacks {member.name} at {version}, "
                                f"below a bitset width"
                            )
                    elif min(value, numbers[member.name]) < numbers[width.name] and numbers[member.name] != value:
                        raise CompilerError(
                            f"{width.enum.module}.py: {qualified(width.enum)}: numbers {member.name} "
                            f"{numbers[member.name]} at {version}, not its value {value}, below a bitset width"
                        )
                return numbers[width.name]
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
        declared = dict.fromkeys(declaration.underlying.name for form in forms for declaration in form.declarations)
        if len(declared) > 1:
            first, second, *_ = declared
            raise CompilerError(
                f"{family.module}.py: {qualified(family)}: declares underlying types {first} and {second}"
            )
        order: dict[str, None] = {}
        for form in forms:
            for declaration in reversed(form.declarations):
                for member in declaration.members:
                    if not member.sentinel:
                        order.setdefault(member.name)
        newest: dict[str, Member] = {}
        lives: dict[str, set[int]] = {}
        for version in reversed(self.versions):
            for form in forms:
                shape = self.live.get((form, version))
                if isinstance(shape, EnumShape):
                    for member in shape.members:
                        newest.setdefault(member.name, member)
                        lives.setdefault(member.name, set()).add(version)
        derived = {name for name, member in newest.items() if isinstance(member.value, MemberRef | Binary)}
        placements: dict[str, dict[tuple[Enum, int], int]] = {}
        for form in forms:
            for version in self.versions:
                shape = self.live.get((form, version))
                if isinstance(shape, EnumShape):
                    for member in shape.members:
                        placements.setdefault(member.name, {})[form, version] = shape.numbers[member.name]
        values: dict[str, int] = {}
        holders: dict[int, list[str]] = {}
        newest_numbers: dict[str, int] = {}
        seen: set[int] = set()
        for version in reversed(self.versions):
            for form in forms:
                shape = self.live.get((form, version))
                if not isinstance(shape, EnumShape):
                    continue
                seen.update(shape.numbers.values())
                for member in shape.members:
                    newest_numbers.setdefault(member.name, shape.numbers[member.name])
                    if member.name in values or member.name in derived:
                        continue
                    number = shape.numbers[member.name]
                    own = placements[member.name]
                    alike = [
                        values[other]
                        for other in values
                        if own.keys() & placements[other].keys()
                        and all(own.get(place, there) == there for place, there in placements[other].items())
                    ]
                    if alike:
                        number = alike[0]
                    elif any(
                        own.get(place, there) != there
                        for other in holders.get(number, [])
                        for place, there in placements[other].items()
                    ):
                        number = max(seen) + 1
                        if number > HIGHEST[underlying.name]:
                            raise CompilerError(
                                f"{form.module}.py: {qualified(form)}.{member.name}: has no library value above "
                                f"{number - 1} that fits {underlying.name}"
                            )
                    values[member.name] = number
                    holders.setdefault(number, []).append(member.name)
                    seen.add(number)
        for name in order:
            match newest[name].value:
                case MemberRef(name=other) | Binary(left=MemberRef(name=other)) if other not in values:
                    values[name] = newest_numbers[name]
                case MemberRef(name=other):
                    values[name] = values[other]
                case Binary(left=MemberRef(name=other), right=Int(value=offset)):
                    values[name] = values[other] - offset
        groups: dict[int, list[str]] = {}
        for name in order:
            groups.setdefault(values[name], []).append(name)
        ranked = {
            value: iter(
                sorted(
                    (name for name in group if name not in derived),
                    key=lambda name: (-max(lives[name]), newest[name].synonym),
                )
            )
            for value, group in groups.items()
        }
        placed: dict[str, None] = {}
        for name in order:
            placed.update(dict.fromkeys(each for each in groups[values[name]] if each in derived))
            if name not in derived:
                placed[next(ranked[values[name]])] = None
        order = placed
        model = EnumModel(
            family,
            underlying,
            tuple(
                newest[name] if name in derived else replace(newest[name], value=Int(values[name])) for name in order
            ),
            {name: values[name] for name in order},
            frozenset(derived),
        )
        library = {values[name] for name in order if name not in derived}
        numberings: dict[tuple[object, ...], Numbering] = {}
        namings: dict[tuple[object, ...], Naming] = {}
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
                aliases = [member for member in shape.members if member.name in derived]
                for member in aliases:
                    value, number = values[member.name], shape.numbers[member.name]
                    if mapped.get(value, number) != number:
                        holder = next(
                            each.name
                            for each in shape.members
                            if each.name not in derived and values[each.name] == value
                        )
                        raise CompilerError(
                            f"{form.module}.py: {qualified(form)}.{member.name}: is numbered {number} at {version}, "
                            f"where {holder} holds its value with {mapped[value]}"
                        )
                    target = next(
                        (
                            each.name
                            for each in shape.members
                            if each.name not in derived and shape.numbers[each.name] == number
                        ),
                        None,
                    )
                    if value not in mapped and target is not None:
                        self.merged.setdefault((form, version), (member.name, target))
                for index, pointer in enumerate(aliases):
                    for earlier in aliases[:index]:
                        shared = values[pointer.name] == values[earlier.name]
                        if shared != (shape.numbers[pointer.name] == shape.numbers[earlier.name]):
                            raise CompilerError(
                                f"{form.module}.py: {qualified(form)}.{pointer.name}: is numbered "
                                f"{shape.numbers[pointer.name]} at {version} and {earlier.name} "
                                f"{shape.numbers[earlier.name]}, but they hold "
                                + ("one library value" if shared else "two library values")
                            )
                free = sorted(set(mapped.values()) - library)
                unused = sorted(library - set(mapped.values()))
                paired = dict(zip(free, unused[: len(free)], strict=True))
                encoded = (
                    {value: number for value, number in mapped.items() if value != number}
                    | paired
                    | {
                        values[member.name]: shape.numbers[member.name]
                        for member in aliases
                        if values[member.name] not in mapped and values[member.name] != shape.numbers[member.name]
                    }
                )
                pointed = {shape.numbers[pointer.name]: values[pointer.name] for pointer in aliases}
                decoded = {
                    number: value
                    for number, value in (
                        {number: value for value, number in mapped.items()}
                        | {number: value for value, number in paired.items()}
                        | pointed
                    ).items()
                    if number != value
                }
                absent = frozenset(library - mapped.keys() - {values[member.name] for member in aliases})
                lossy = frozenset(unused[len(free) :])
                numbering = numberings.setdefault(
                    (
                        shape.underlying,
                        tuple(sorted(encoded.items())),
                        tuple(sorted(decoded.items())),
                        absent,
                        lossy,
                    ),
                    Numbering(model, encoded, decoded, absent, lossy, not (encoded or decoded or absent or lossy)),
                )
                self.numbered[form, version] = numbering
                spans.setdefault(numbering, set()).add(version)
                if form in self.name_coded:
                    canonical: dict[int, str] = {}
                    for member in sorted(
                        shape.members,
                        key=lambda member: (not isinstance(member.value, MemberRef | Binary), member.synonym),
                    ):
                        canonical.setdefault(shape.numbers[member.name], member.encoded_name)
                    names = {member.name: member.encoded_name for member in shape.members}
                    written = {value: canonical[number] for value, number in mapped.items()} | {
                        values[member.name]: canonical[shape.numbers[member.name]]
                        for member in aliases
                        if values[member.name] not in mapped
                    }
                    inverse = {number: value for value, number in mapped.items()}
                    read = {
                        member.encoded_name: values[member.name]
                        if member.name in derived
                        else inverse[shape.numbers[member.name]]
                        for member in shape.members
                    }
                    naming = namings.setdefault(
                        (frozenset(names.items()), frozenset(written.items()), frozenset(read.items())),
                        Naming(model, names, written, read),
                    )
                    self.named[form, version] = naming
                    spans.setdefault(naming, set()).add(version)
            model.runs[form] = self.ranges([version for version in self.versions if (form, version) in self.live])
        for coding, versions in spans.items():
            coding.runs = self.ranges(versions)
            coding.since = min(versions)
        self.model_numberings[model] = sorted(numberings.values(), key=lambda numbering: numbering.since)
        self.model_namings[model] = sorted(namings.values(), key=lambda naming: naming.since)
        primary = next(iter(model.runs.values()))
        model.since = primary[0].since
        model.versioned = primary != [ALWAYS]

    def project_struct(
        self,
        family: Struct,
        models: dict[tuple[object, ...], StructModel],
        encodings: dict[tuple[object, ...], Encoding],
    ) -> None:
        for version in self.versions:
            shape = self.live.get((family, version))
            if not isinstance(shape, StructShape):
                continue
            nested = tuple(
                self.struct_models[child, version] if isinstance(child, Struct) else self.enum_type(child, version)
                for child in family.nested
                if (child, version) in self.live
            )
            slots = frozenset(
                (each.name, self.resolved(strip(each.type), version))
                for each in shape.fields
                if not isinstance(each.type, Literal)
            )
            model = models.setdefault((self.pair(family), slots, nested), StructModel(family, (), nested))
            self.struct_models[family, version] = model
            self.encoded[family, version] = self.project_encoding(
                family, model, shape.fields, version, encodings, manual=shape.manual
            )

    def project_encoding(
        self,
        family: Struct,
        model: StructModel,
        fields: tuple[Field, ...],
        version: int,
        encodings: dict[tuple[object, ...], Encoding],
        excluded: str | None = None,
        manual: bool = False,
    ) -> Encoding:
        sentinels: dict[MemberRef, int] = {}
        for each in fields:
            for operator, operand, other in operands(each.when):
                read = other if isinstance(operand, MemberRef) else operand
                held = next(
                    (earlier.type for earlier in fields if isinstance(read, FieldRef) and earlier.name == read.name),
                    None,
                )
                if isinstance(held, EnumRef | EnumName) and (held.enum, version) in self.merged:
                    derived, target = self.merged[held.enum, version]
                    raise CompilerError(
                        f"{family.module}.py: {qualified(family)}.{each.name}: compares a value of "
                        f"{qualified(held.enum)} at {version}, where {derived} encodes to {target}'s number"
                    )
                if isinstance(operand, MemberRef):
                    if not (
                        isinstance(held, EnumRef | EnumName)
                        and self.family_models[held.enum][0] is self.family_models[operand.enum][0]
                    ):
                        raise CompilerError(
                            f"{family.module}.py: {qualified(family)}.{each.name}: compares "
                            f"{qualified(operand.enum)}.{operand.name} with a value of another type"
                        )
                    if operand.name not in self.enum_models[operand.enum, version].values:
                        number = self.numbers[operand.enum, version][operand.name]
                        numbering = self.numbered[held.enum, version]
                        if number in numbering.lossy:
                            raise CompilerError(
                                f"{family.module}.py: {qualified(family)}.{each.name}: compares "
                                f"{qualified(operand.enum)}.{operand.name}, numbered {number} at {version}, which "
                                "decodes to no value"
                            )
                        sentinels[operand] = numbering.decoded.get(number, number)
                elif (
                    isinstance(held, EnumRef | EnumName)
                    and not (operator in ("==", "!=") and isinstance(other, MemberRef))
                    and (self.numbered[held.enum, version].encoded or self.numbered[held.enum, version].decoded)
                ):
                    raise CompilerError(
                        f"{family.module}.py: {qualified(family)}.{each.name}: reads {operand.name} as a number "
                        f"at {version}, where {qualified(held.enum)} numbers a value apart from it"
                    )
        reached: dict[StructRef | EnumRef | EnumName, Encoding | Numbering | Naming] = {}
        key = tuple(
            (
                each.name,
                self.coded(each.type, version, reached),
                self.coded(each.when, version, reached),
                self.coded(each.duplicate, version, reached),
            )
            for each in fields
        )
        numbers = {
            member: self.numbers[member.enum, version][member.name]
            for each in fields
            for member in (*numbered_by(each.type), *numbered_by(each.when), *numbered_by(each.duplicate))
        }
        return encodings.setdefault(
            (model, key, frozenset(sentinels.items()), manual),
            Encoding(model, fields, reached, numbers | sentinels, excluded=excluded, manual=manual),
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
                key: tuple[object, ...] = (present, nested, reached, struct_declaration.manual)
                candidate: Shape = StructShape(family, present, nested, struct_declaration.manual)
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
