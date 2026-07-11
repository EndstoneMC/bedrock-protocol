"""Bedrock-protocol IR — the language-agnostic boundary between frontend and backend.

Analog of protoc's `descriptor.{h,cc}`. The frontend (`compiler.parser`)
produces a `File`; the resolver (`compiler.resolver`) refines it into a
`ResolvedFile`, the only descriptor type a backend receives.

Every dataclass is frozen. Each field carries one `FieldType` tree describing
both the shape the user wrote (`X | None` → `OptionalType`, `list[T]` →
`RepeatedType`, `A | B` → `VariantType`) and the encoding it takes on the wire.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping

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

#: Primitives that may length-prefix a list or string.
INTEGER_PRIMITIVES: frozenset[str] = PRIMITIVES - frozenset({"str", "bytes", "bool", "float", "double"})


class CompilerError(Exception):
    """A schema-level error surfaced to the user without a traceback."""


# --- field type tree ---------------------------------------------------------


@dataclass(frozen=True)
class PrimitiveType:
    """A DSL primitive. `str` / `bytes` are length-prefixed; numeric primitives
    are fixed-width or varint (`name in VARINT_PRIMITIVES`).

    `alias` is set when the field references a `type Name = <primitive>`
    declaration: `name` drives the wire encoding, but a backend spells the
    field with the alias name (so `Color = int32` serializes as `int32` yet the
    C++ field type reads `Color`)."""

    name: str
    alias: str | None = None
    kind: Literal["primitive"] = "primitive"

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
    that many elements."""

    inner: "FieldType"
    prefix: PrimitiveType = field(default_factory=lambda: PrimitiveType(name="uvarint32"))
    kind: Literal["repeated"] = "repeated"

    @property
    def referenced(self) -> frozenset[str]:
        return self.inner.referenced


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


FieldType = PrimitiveType | StructType | EnumType | OptionalType | RepeatedType | VariantType


# --- declarations ------------------------------------------------------------


@dataclass(frozen=True)
class EnumValue:
    name: str
    number: int

    @property
    def wire_name(self) -> str:
        """The string a name-coded enum puts on the wire. BDS cereal serializes
        an enum by its verbatim member name (confirmed in the 1.26.20 binary:
        BoolAttributeOperation binds "OVERRIDE"/"ALPHA_BLEND"/... unchanged)."""
        return self.name


@dataclass(frozen=True)
class Enum:
    name: str
    values: tuple[EnumValue, ...]

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset()

    @property
    def change_points(self) -> frozenset[int]:
        return frozenset()

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
    name: str
    fields: tuple[Field, ...]
    packet_id: int | None = None
    since: int | None = None
    until: int | None = None

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset().union(
            *(version.type.referenced for f in self.fields for version in f.versions if version.type is not None)
        )

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


@dataclass
class FileSet:
    """Every loaded file plus the subset marked for output. Analog of protoc's
    `DescriptorPool`, narrowed to the import graph and a resolve memo."""

    files: Mapping[str, File]
    outputs: tuple[str, ...]
    version: int | None = None
    resolved: dict[str, "ResolvedFile"] = field(default_factory=dict)


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
    """The post-resolver boundary delivered to backends: version snapshots,
    topological order, and the FileSet for cross-file lookup."""

    file: File
    file_set: FileSet
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
            other = self.file_set.files.get(imp)
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
            other = self.file_set.resolved.get(imp)
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
            other = self.file_set.resolved.get(imp)
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
