"""Bedrock-protocol IR — the language-agnostic boundary between frontend and backend.

Analog of protoc's `descriptor.{h,cc}`. The frontend (`compiler.parser`)
produces a `File`; the resolver (`compiler.resolver`) refines it into a
`ResolvedFile`, the only descriptor type a backend receives.

Every dataclass is frozen. Each field carries one `FieldType` tree describing
both the shape the user wrote (`X | None` → `OptionalType`, `list[T]` →
`RepeatedType`, `dict[K, V]` → `MappingType`, `A | B` → `VariantType`) and the
encoding it takes on the wire.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Mapping

if TYPE_CHECKING:
    from bedrock_protocol.compiler.descriptor_pool import DescriptorPool

# --- primitives ---------------------------------------------------------------

#: DSL primitive names. `str` / `bytes` are length-prefixed; the rest numeric/bool.
PRIMITIVES: frozenset[str] = frozenset(
    {
        "str",
        "bytes",
        "int",
        "bool",
        "float",
        "double",
        "varint32",
        "varint64",
        "uvarint32",
        "uvarint64",
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
    }
)

#: Primitives carried as LEB128 (zigzag for signed) rather than fixed-width.
VARINT_PRIMITIVES: frozenset[str] = frozenset(
    {
        "varint32",
        "varint64",
        "uvarint32",
        "uvarint64",
    }
)

#: Annotations that name a compiler builtin: the DSL spells the stdlib type it
#: stands in for, and each backend maps it to its own hand-written implementation
#: rather than emitting a definition. Language-agnostic here; the C++ spelling and
#: header live in the cpp backend.
BUILTIN_ANNOTATIONS: dict[str, str] = {"uuid.UUID": "UUID"}

#: Primitives that may length-prefix a list or string.
INTEGER_PRIMITIVES: frozenset[str] = PRIMITIVES - frozenset({"str", "bytes", "bool", "float", "double"})

#: Byte order of a fixed-width encoding.
Endian = Literal["little", "big"]


class CompilerError(Exception):
    """A schema-level error surfaced to the user without a traceback."""


# --- predicate tree ----------------------------------------------------------


@dataclass(frozen=True)
class Predicate:
    """A `when=` predicate as a small expression tree. `kind` is either a leaf
    (`field`, `enum`, `int`) or an operator (`==`, `!=`, `<`, `>`, `<=`, `>=`,
    `and`, `or`, `not`)."""

    kind: str
    text: str = ""
    operands: tuple["Predicate", ...] = ()

    @property
    def referenced(self) -> frozenset[str]:
        """Enums the predicate names, so a struct gating on one orders after it
        and inherits its versioning."""
        if self.kind == "enum":
            return frozenset({self.text.rsplit(".", 1)[0]})
        return frozenset().union(*(o.referenced for o in self.operands))


# --- field type tree ---------------------------------------------------------


@dataclass(frozen=True)
class PrimitiveType:
    """A DSL primitive. `str` / `bytes` are length-prefixed; numeric primitives
    are fixed-width or varint (`name in VARINT_PRIMITIVES`).

    `alias` is set when the field references a `type Name = <primitive>`
    declaration: `name` drives the wire encoding, but a backend spells the
    field with the alias name (so `Color = int32` serializes as `int32` yet the
    C++ field type reads `Color`).

    `wire` is set by `field(type=<integer primitive>)`: `name` keeps owning the
    in-memory type and `wire` takes over the encoding, so a BDS member declared
    narrow but written as a varint keeps both halves.

    `endian` is the byte order of a fixed-width encoding, set by
    `field(endian="big")` for the few fields Bedrock sends big-endian."""

    name: str
    alias: str | None = None
    wire: str | None = None
    endian: Endian = "little"
    kind: Literal["primitive"] = "primitive"

    @property
    def encoding(self) -> str:
        """The primitive the value takes on the wire — its own, unless
        `field(type=)` overrode it."""
        return self.wire if self.wire is not None else self.name

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset({self.alias}) if self.alias is not None else frozenset()


@dataclass(frozen=True)
class StructType:
    """A reference to a user-defined struct."""

    name: str
    kind: Literal["struct"] = "struct"

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset({self.name})


@dataclass(frozen=True)
class EnumType:
    """A reference to a user-defined enum. `scalar=None` means name-coded
    (string on the wire); `scalar` set means integer-coded over that primitive."""

    name: str
    scalar: PrimitiveType | None
    kind: Literal["enum"] = "enum"

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset({self.name})


@dataclass(frozen=True)
class OptionalType:
    """`T | None` → a one-byte bool presence flag followed by the payload."""

    inner: "FieldType"
    kind: Literal["optional"] = "optional"

    @property
    def referenced(self) -> frozenset[str]:
        return self.inner.referenced


@dataclass(frozen=True)
class RepeatedType:
    """`list[T]` — a length prefix (`prefix`, default `uvarint32`) followed by
    that many elements.

    `count` replaces the prefix with an expression over earlier fields: nothing
    on the wire marks the length, and both sides recompute it -- for a list whose
    count BDS wrote somewhere else."""

    inner: "FieldType"
    prefix: PrimitiveType = field(default_factory=lambda: PrimitiveType(name="uvarint32"))
    count: "Predicate | None" = None
    kind: Literal["repeated"] = "repeated"

    @property
    def referenced(self) -> frozenset[str]:
        own = self.count.referenced if self.count is not None else frozenset()
        return self.inner.referenced | own


@dataclass(frozen=True)
class MappingType:
    """`dict[K, V]` — a length prefix (`prefix`, default `uvarint32`) followed
    by that many key/value pairs, each key immediately preceding its value."""

    key: "FieldType"
    value: "FieldType"
    prefix: PrimitiveType = field(default_factory=lambda: PrimitiveType(name="uvarint32"))
    kind: Literal["mapping"] = "mapping"

    @property
    def referenced(self) -> frozenset[str]:
        return self.key.referenced | self.value.referenced


@dataclass(frozen=True)
class VariantType:
    """`A | B | C` → a `std::variant`-shaped tagged union. `discriminator` is
    the integer primitive prefixing the active case index on the wire (default
    `uvarint32`); a `None` case carries no payload (`std::monostate`)."""

    cases: tuple["FieldType | None", ...]
    discriminator: PrimitiveType = field(default_factory=lambda: PrimitiveType(name="uvarint32"))
    kind: Literal["variant"] = "variant"

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset().union(*(a.referenced for a in self.cases if a is not None))


@dataclass(frozen=True)
class CondType:
    """Present only when `predicate` holds against earlier fields of the same
    struct. Nothing marks presence on the wire -- both sides recompute it, so
    the field is spelled as its bare payload rather than an optional.

    `group` is the index of the `with field(when=...)` block the field came
    from; fields sharing it emit under one `if`. `None` is a lone
    `field(when=)`."""

    inner: "FieldType"
    predicate: Predicate
    group: int | None = None
    kind: Literal["cond"] = "cond"

    @property
    def referenced(self) -> frozenset[str]:
        return self.inner.referenced | self.predicate.referenced


FieldType = PrimitiveType | StructType | EnumType | OptionalType | RepeatedType | MappingType | VariantType | CondType


# --- declarations ------------------------------------------------------------


@dataclass(frozen=True)
class EnumValue:
    """`since` / `until` bound the member to `[since, until)`, for a value BDS
    added or removed at a known protocol version."""

    name: str
    number: int
    since: int | None = None
    until: int | None = None
    #: Spelled `auto()`: the number is `previous + 1` within whichever snapshot the
    #: member appears in, so a trailing sentinel tracks the members present there.
    is_auto: bool = False

    def present_at(self, snapshot: int) -> bool:
        return (self.since is None or snapshot >= self.since) and (self.until is None or snapshot < self.until)

    @property
    def wire_name(self) -> str:
        """The string a name-coded enum puts on the wire. BDS cereal serializes
        an enum by its verbatim member name (confirmed in the 1.26.20 binary:
        BoolAttributeOperation binds "OVERRIDE"/"ALPHA_BLEND"/... unchanged)."""
        return self.name


@dataclass(frozen=True)
class Enum:
    """`underlying` is the enum's C++ underlying type, spelled as a second base
    (`class MemoryCategory(IntEnum, uint8)`); `None` means the C++ default, `int`."""

    name: str
    values: tuple[EnumValue, ...]
    underlying: PrimitiveType | None = None

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset()

    @property
    def change_points(self) -> frozenset[int]:
        """Versions where a member appears or disappears, so an enum whose members
        are gated is versioned like a struct whose fields are."""
        points: set[int] = set()
        for v in self.values:
            if v.since is not None:
                points.add(v.since)
            if v.until is not None:
                points.add(v.until)
        return frozenset(points)

    #: Change points affecting the on-wire shape (same as change_points here).
    shape_change_points = change_points


@dataclass(frozen=True)
class FieldVersion:
    """One version of a field — its declared type tree over the half-open
    protocol range `[since, until)`. A version-invariant field has one entry;
    a `field(since=)`-gated field has one entry with a bounded range."""

    type: FieldType | None
    since: int | None
    until: int | None


@dataclass(frozen=True)
class Field:
    name: str
    versions: tuple[FieldVersion, ...]

    def version_at(self, snapshot: int) -> FieldVersion | None:
        for version in self.versions:
            lo = version.since or 0
            if lo <= snapshot and (version.until is None or snapshot < version.until):
                return version
        return None

    def present_at(self, snapshot: int) -> bool:
        return self.version_at(snapshot) is not None

    @property
    def type_single(self) -> FieldType | None:
        """Type tree of a single-version field. Caller asserts one version."""
        (version,) = self.versions
        return version.type


@dataclass(frozen=True)
class Struct:
    """`builtin` marks a type the compiler must not define: it emits no struct and
    no serializer, references the name as-is, and trusts a hand-written definition
    plus `Serializer` specialization in the matching `<bedrock/*.hpp>` header.

    `nested` holds the types BDS declares inside the class, in source order; a
    reference to one carries the dotted `Owner.Inner` name."""

    name: str
    fields: tuple[Field, ...]
    packet_id: int | None = None
    since: int | None = None
    until: int | None = None
    builtin: bool = False
    nested: tuple["Enum | Struct", ...] = ()

    @property
    def referenced(self) -> frozenset[str]:
        own = frozenset().union(
            *(version.type.referenced for f in self.fields for version in f.versions if version.type is not None)
        )
        # A nested type's own references are the owner's too, so cross-file
        # includes and topological order treat them like any other field type.
        return own.union(*(t.referenced for t in self.nested))

    @property
    def change_points(self) -> frozenset[int]:
        points: set[int] = set()
        if self.since is not None:
            points.add(self.since)
        if self.until is not None:
            points.add(self.until)
        for f in self.fields:
            for version in f.versions:
                if version.since is not None:
                    points.add(version.since)
                if version.until is not None:
                    points.add(version.until)
        for t in self.nested:
            points |= t.change_points
        return frozenset(points)

    #: Change points affecting the on-wire shape (same as change_points here).
    shape_change_points = change_points


@dataclass(frozen=True)
class PrimitiveAlias:
    """`type Name = <primitive>`. Rendered as `enum Name : ctype {}` in C++: a
    distinct integer type wire-compatible with the underlying primitive, so a
    user may specialize `Serializer<Name>` apart from the primitive's."""

    name: str
    primitive: str


@dataclass(frozen=True)
class TypeAlias:
    """`type Name = <non-primitive>`. Rendered as `using Name = ctype`;
    `target` is the single field-type tree."""

    name: str
    target: FieldType


@dataclass(frozen=True)
class File:
    """One `.py` file's contribution to the schema. `imports` carry dotted
    names of other loaded files this one draws types from."""

    name: str  # dotted module name
    stem: str  # output filename stem
    package: str | None  # output namespace
    enums: tuple[Enum, ...]
    structs: tuple[Struct, ...]
    primitive_aliases: tuple[PrimitiveAlias, ...]
    type_aliases: tuple[TypeAlias, ...]
    imports: tuple[str, ...]
    declaration_order: tuple[str, ...]  # type names in source order


@dataclass(frozen=True)
class FileSet:
    """Every parsed file plus the subset marked for output -- protoc's
    `FileDescriptorSet`. Pure data: the built descriptors live in the
    `DescriptorPool`, not here."""

    files: Mapping[str, File]
    outputs: tuple[str, ...]
    version: int | None = None


# --- resolved descriptors (post-versioning) -----------------------------------


@dataclass(frozen=True)
class VersionSnapshot:
    """One version of a type. `lo` is `since` (inclusive), `hi` is `until`
    (exclusive); `hi=None` is open-ended. `is_fresh` marks snapshots whose
    definition is a new shape rather than a re-use of an earlier one."""

    lo: int
    hi: int | None
    is_fresh: bool
    concrete: int  # snapshot where this shape was first emitted
    enum: Enum | None = None
    struct: Struct | None = None


@dataclass(frozen=True)
class ResolvedFile:
    """A cross-referenced file -- protoc's `FileDescriptor` to `File`'s
    `FileDescriptorProto`. Carries version snapshots and topological order, and
    reaches its imports through `pool`, protoc's `FileDescriptor::pool()`."""

    file: File
    pool: "DescriptorPool"
    declaration_order: tuple[str, ...]  # versioned topo order
    versioned_types: frozenset[str]
    snapshots: tuple[int, ...]  # global snapshot points
    snapshots_by_type: Mapping[str, tuple[VersionSnapshot, ...]]

    def lookup(self, name: str) -> Enum | Struct | None:
        for e in self.file.enums:
            if e.name == name:
                return e
        for s in self.file.structs:
            if s.name == name:
                return s
        for imp in self.file.imports:
            other = self.pool.file_set.files.get(imp)
            if other is None:
                continue
            for e in other.enums:
                if e.name == name:
                    return e
            for s in other.structs:
                if s.name == name:
                    return s
        return None

    def is_versioned(self, name: str, _seen: frozenset[str] = frozenset()) -> bool:
        if name in self.versioned_types:
            return True
        seen = _seen | {self.file.name}
        for imp in self.file.imports:
            if imp in seen:  # stop at an import cycle
                continue
            other = self.pool.find_file_by_name(imp)
            if other is not None and other.is_versioned(name, seen):
                return True
        return False

    def snapshots_of(self, name: str, _seen: frozenset[str] = frozenset()) -> tuple[VersionSnapshot, ...]:
        own = self.snapshots_by_type.get(name)
        if own is not None:
            return own
        seen = _seen | {self.file.name}
        for imp in self.file.imports:
            if imp in seen:
                continue
            other = self.pool.find_file_by_name(imp)
            if other is None:
                continue
            snaps = other.snapshots_of(name, seen)
            if snaps:
                return snaps
        return ()

    def present_at(self, name: str, snapshot: int) -> VersionSnapshot | None:
        snaps = self.snapshots_of(name)
        for s in snaps:
            if s.lo == snapshot:
                return s
        for s in snaps:
            if s.lo <= snapshot and (s.hi is None or snapshot < s.hi):
                return s
        return None

    def fresh_snapshots(self, name: str) -> tuple[VersionSnapshot, ...]:
        return tuple(s for s in self.snapshots_of(name) if s.is_fresh)
