"""Language-agnostic protocol IR.

The frontend turns griffe-parsed DSL modules into this model; a backend lowers
it to a target language. Nothing here is C++-specific. A type's declared shape
lives in `TypeRef`; how it travels on the wire lives in `Wire`. The two are
kept apart so a backend can spell a struct member from one and a serializer
body from the other without re-deriving either.
"""

from dataclasses import dataclass

#: DSL primitive names. `str` is length-prefixed; the rest are numeric/bool.
PRIMITIVES: frozenset[str] = frozenset(
    {
        "str", "int", "bool", "float", "double",
        "varint32", "varint64", "uvarint32", "uvarint64",
        "int8", "int16", "int32", "int64",
        "uint8", "uint16", "uint32", "uint64",
    }
)

#: Primitives carried as LEB128 (zigzag for signed) rather than fixed-width.
VARINT_PRIMITIVES: frozenset[str] = frozenset(
    {"varint32", "varint64", "uvarint32", "uvarint64"}
)


class CompilerError(Exception):
    """A schema-level error surfaced to the user without a traceback."""


# --- type references: a field's declared shape -------------------------------


@dataclass(frozen=True)
class Primitive:
    name: str

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset()


@dataclass(frozen=True)
class Named:
    """A reference to a user-defined struct, enum, or alias."""

    name: str

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset({self.name})


@dataclass(frozen=True)
class Optional:
    inner: "TypeRef"

    @property
    def referenced(self) -> frozenset[str]:
        return self.inner.referenced


@dataclass(frozen=True)
class Repeated:
    """A repeated field's declared shape: `list[T]` when `count` is None, a
    fixed-length `tuple[T, ...]` of identical types when `count` is set."""

    inner: "TypeRef"
    count: int | None

    @property
    def referenced(self) -> frozenset[str]:
        return self.inner.referenced


@dataclass(frozen=True)
class Mapping:
    """A `dict[K, V]` field's declared shape."""

    key: "TypeRef"
    value: "TypeRef"

    @property
    def referenced(self) -> frozenset[str]:
        return self.key.referenced | self.value.referenced


@dataclass(frozen=True)
class Variant:
    """A tagged-union field's declared shape: a `std::variant` over `arms`,
    indexed by a discriminator. A None arm is an absent case (`std::monostate`)."""

    arms: "tuple[TypeRef | None, ...]"

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset().union(
            *(a.referenced for a in self.arms if a is not None)
        )


TypeRef = Primitive | Named | Optional | Repeated | Mapping | Variant


# --- predicates: a field's data-dependent presence condition -----------------


@dataclass(frozen=True)
class Pred:
    """A `when=` predicate as a small expression tree. `kind` is either a leaf
    type -- `field`, `enum`, `int` -- or an operator: a comparison (`==`,
    `!=`, `<`, `>`, `<=`, `>=`), `and`, `or`, or `not`. A leaf carries its
    payload in `text` (a field name, a dotted `Enum.MEMBER`, or an integer);
    an operator carries its children in `operands`. The frontend builds this
    from the parsed lambda so a backend never sees the DSL's surface syntax."""

    kind: str
    text: str = ""
    operands: "tuple[Pred, ...]" = ()


# --- wire encodings: how a field travels on the wire -------------------------


@dataclass(frozen=True)
class Scalar:
    """A fixed-width or varint numeric/bool primitive."""

    primitive: str
    varint: bool
    big_endian: bool = False


@dataclass(frozen=True)
class Str:
    """A varuint32 length prefix followed by UTF-8 bytes."""


@dataclass(frozen=True)
class StructRef:
    """A nested struct, encoded through its own serializer."""

    name: str


@dataclass(frozen=True)
class EnumRef:
    """An enum field. `scalar` None means name-coded (the enumerator name
    travels as a string); otherwise the enum is integer-coded over `scalar`."""

    name: str
    scalar: Scalar | None


@dataclass(frozen=True)
class Opt:
    """An optional payload. `discriminator` picks the presence encoding:
    False is a one-byte bool flag (true present). True is a varuint union
    index, where `present_tag` is the index that means present and the other
    index means absent -- `T | None` makes present 0, `None | T` makes it 1."""

    inner: "Wire"
    discriminator: bool
    present_tag: int = 0


@dataclass(frozen=True)
class Repeat:
    """A repeated payload. `count` None is a length-prefixed list: the element
    count travels first as `prefix` (a length scalar), then the elements. A set
    `count` is a fixed-length array of exactly that many elements, no prefix."""

    inner: "Wire"
    prefix: Scalar | None
    count: int | None


@dataclass(frozen=True)
class Map:
    """A length-prefixed map: the pair count travels first as `prefix` (a
    length scalar), then that many key encodings each followed by its value."""

    key: "Wire"
    value: "Wire"
    prefix: Scalar


@dataclass(frozen=True)
class Switch:
    """A tagged union: a varuint32 discriminator selects one of `arms` by
    index, then that arm's payload follows. A None arm carries no payload."""

    arms: "tuple[Wire | None, ...]"


@dataclass(frozen=True)
class Cond:
    """A field present only when `predicate` holds against earlier fields.
    Unlike `Opt`, no presence marker travels on the wire -- both sides
    recompute presence from the same predicate. The field's declared type is
    an `Optional`: it may be absent."""

    inner: "Wire"
    predicate: Pred


Wire = Scalar | Str | StructRef | EnumRef | Opt | Repeat | Map | Switch | Cond


# --- declarations ------------------------------------------------------------


@dataclass(frozen=True)
class EnumMember:
    name: str
    value: int
    since: int | None
    until: int | None

    @property
    def wire_name(self) -> str:
        """The string a name-coded enum puts on the wire."""
        return self.name.lower().replace("_", "")


@dataclass(frozen=True)
class Enum:
    name: str
    members: tuple[EnumMember, ...]
    since: int | None

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset()

    @property
    def change_points(self) -> frozenset[int]:
        points = {self.since} if self.since is not None else set()
        for m in self.members:
            if m.since is not None:
                points.add(m.since)
            if m.until is not None:
                points.add(m.until)
        return frozenset(points)


@dataclass(frozen=True)
class FieldArm:
    """One version era of a field: its declared type and wire encoding over
    the half-open protocol range `[since, until)`. A field with a single,
    version-invariant shape has one arm; a field redeclared per era has one
    arm per declaration."""

    type: TypeRef | None
    wire: Wire | None
    since: int | None
    until: int | None


@dataclass(frozen=True)
class Field:
    """A struct field. `arms` are version-disjoint eras in ascending order;
    the field is present at a snapshot when one arm covers it."""

    name: str
    arms: tuple[FieldArm, ...]

    def arm_at(self, snapshot: int) -> FieldArm | None:
        """The arm covering `snapshot`, or None when the field is absent."""
        for arm in self.arms:
            lo = arm.since or 0
            if lo <= snapshot and (arm.until is None or snapshot < arm.until):
                return arm
        return None

    def present_at(self, snapshot: int) -> bool:
        return self.arm_at(snapshot) is not None

    @property
    def type(self) -> TypeRef | None:
        """The declared type. Valid only on a single-arm field -- an
        unversioned field, or one narrowed to a snapshot."""
        (arm,) = self.arms
        return arm.type

    @property
    def wire(self) -> Wire | None:
        """The wire encoding. Valid only on a single-arm field."""
        (arm,) = self.arms
        return arm.wire


@dataclass(frozen=True)
class Struct:
    name: str
    fields: tuple[Field, ...]
    enums: tuple[Enum, ...]  # nested, version-invariant
    packet_id: int | None
    since: int | None = None  # protocol version that introduced the packet

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset().union(
            *(
                arm.type.referenced
                for f in self.fields
                for arm in f.arms
                if arm.type is not None
            )
        )

    @property
    def change_points(self) -> frozenset[int]:
        points: set[int] = set()
        for f in self.fields:
            for arm in f.arms:
                if arm.since is not None:
                    points.add(arm.since)
                if arm.until is not None:
                    points.add(arm.until)
        if self.since is not None:
            points.add(self.since)
        return frozenset(points)


@dataclass(frozen=True)
class Alias:
    """A module-level `type Name = <primitive>` declaration."""

    name: str
    primitive: str


@dataclass(frozen=True)
class Module:
    name: str  # dotted, e.g. protocol.actor
    stem: str  # input file stem, drives the output filename
    package: str | None
    types: tuple[Enum | Struct, ...]  # declaration order
    aliases: tuple[Alias, ...]
    imports: tuple[str, ...]  # dotted names of loaded modules it draws types from

    @property
    def enums(self) -> tuple[Enum, ...]:
        return tuple(t for t in self.types if isinstance(t, Enum))

    @property
    def structs(self) -> tuple[Struct, ...]:
        return tuple(t for t in self.types if isinstance(t, Struct))


@dataclass(frozen=True)
class Schema:
    """Every loaded module, the subset that should produce output, and the
    names marked `@builtin` -- types the compiler references but never defines,
    trusting a hand-written struct and `Serializer` in `<bedrock/nbt.hpp>`."""

    modules: dict[str, Module]
    outputs: tuple[str, ...]
    builtins: frozenset[str]
