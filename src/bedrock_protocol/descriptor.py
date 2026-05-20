"""Bedrock-protocol IR — the language-agnostic boundary between frontend and backend.

This module is the analog of protoc's `descriptor.{h,cc}`. The frontend
(`compiler.parser`) produces a `File`; the resolver (`compiler.resolver`)
refines it into a `ResolvedFile`, which is the only descriptor type a
backend receives.

Every dataclass here is frozen and read-only. Each field carries a single
`FieldType` tree that describes both the shape the user wrote (`X | None`
→ `OptionalType`, `list[T]` → `RepeatedType`, ...) and the encoding it
takes on the wire (presence-bit vs union-tag for optionals, length prefix
for lists, endianness for scalars, ...). One tree, one walk.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

# --- primitives ---------------------------------------------------------------

#: DSL primitive names. `str` and `bytes` are length-prefixed UTF-8 / opaque
#: buffers; the rest are numeric or boolean.
PRIMITIVES: frozenset[str] = frozenset({
    "str", "bytes", "int", "bool", "float", "double",
    "varint32", "varint64", "uvarint32", "uvarint64",
    "int8", "int16", "int32", "int64",
    "uint8", "uint16", "uint32", "uint64",
})

#: Primitives carried as LEB128 (zigzag for signed) rather than fixed-width.
VARINT_PRIMITIVES: frozenset[str] = frozenset({
    "varint32", "varint64", "uvarint32", "uvarint64",
})

#: Primitives that may length-prefix a list, map, or string.
INTEGER_PRIMITIVES: frozenset[str] = PRIMITIVES - frozenset({
    "str", "bytes", "bool", "float", "double",
})


class CompilerError(Exception):
    """A schema-level error surfaced to the user without a traceback."""


# --- predicate trees ---------------------------------------------------------


@dataclass(frozen=True)
class Predicate:
    """A `when=` predicate as a small expression tree.

    `kind` is either a leaf (`field`, `enum`, `int`) or an operator
    (`==`, `!=`, `<`, `>`, `<=`, `>=`, `and`, `or`, `not`).
    """
    kind: str
    text: str = ""
    operands: tuple["Predicate", ...] = ()


# --- field type tree ---------------------------------------------------------


@dataclass(frozen=True)
class PrimitiveType:
    """A DSL primitive. `str` / `bytes` are length-prefixed; the rest are
    fixed-width or varint (varint-ness derives from `name in VARINT_PRIMITIVES`).
    `big_endian` only applies to fixed-width numeric primitives.

    `alias` is set when this field references a `type Name = <primitive>`
    declaration: `name` still drives the wire encoding (so a `Color = int32`
    serializes as `int32`), but a backend spells the field with the alias
    name (so the C++ field type is `Color`, not `std::int32_t`).
    """
    name: str
    big_endian: bool = False
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
    (string on the wire); `scalar` set means integer-coded over that
    primitive."""
    name: str
    scalar: PrimitiveType | None
    kind: Literal["enum"] = "enum"

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset({self.name})


@dataclass(frozen=True)
class OptionalType:
    """`discriminator=False` → one-byte bool flag; True → varuint union tag.

    With a union tag, `present_tag` is the tag value that means "payload
    follows" (0 for `T | None`, 1 for `None | T`).
    """
    inner: "FieldType"
    discriminator: bool = False
    present_tag: int = 0
    kind: Literal["optional"] = "optional"

    @property
    def referenced(self) -> frozenset[str]:
        return self.inner.referenced


@dataclass(frozen=True)
class RepeatedType:
    """`list[T]` when `count` is None and `prefix` carries the length wire;
    `tuple[T, ..., T]` when `count` is set and `prefix` is None (fixed array)."""
    inner: "FieldType"
    count: int | None = None
    prefix: PrimitiveType | None = None
    kind: Literal["repeated"] = "repeated"

    @property
    def referenced(self) -> frozenset[str]:
        return self.inner.referenced


@dataclass(frozen=True)
class MappingType:
    """Length-prefixed map of key/value pairs."""
    key: "FieldType"
    value: "FieldType"
    prefix: PrimitiveType
    kind: Literal["mapping"] = "mapping"

    @property
    def referenced(self) -> frozenset[str]:
        return self.key.referenced | self.value.referenced


@dataclass(frozen=True)
class VariantType:
    """`std::variant`-shaped tagged union with a varuint32 tag. A None arm
    carries no payload (`std::monostate` in C++)."""
    arms: tuple["FieldType | None", ...]
    kind: Literal["variant"] = "variant"

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset().union(
            *(a.referenced for a in self.arms if a is not None)
        )


@dataclass(frozen=True)
class CondType:
    """Field present only when `predicate` holds against earlier fields.
    No presence marker on the wire — both sides recompute it.

    `group` is the index of the `with field(when=...)` block the field came
    from; fields sharing it form one guarded region. None is a lone
    `field(when=)`.
    """
    inner: "FieldType"
    predicate: Predicate
    group: int | None = None
    kind: Literal["cond"] = "cond"

    @property
    def referenced(self) -> frozenset[str]:
        return self.inner.referenced


FieldType = (
    PrimitiveType | StructType | EnumType | OptionalType | RepeatedType
    | MappingType | VariantType | CondType
)


# --- declarations ------------------------------------------------------------


@dataclass(frozen=True)
class EnumValue:
    name: str
    number: int
    since: int | None
    until: int | None

    @property
    def wire_name(self) -> str:
        """The string a name-coded enum puts on the wire."""
        return self.name.lower().replace("_", "")


@dataclass(frozen=True)
class Enum:
    name: str
    values: tuple[EnumValue, ...]
    since: int | None = None

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset()

    @property
    def change_points(self) -> frozenset[int]:
        points: set[int] = set()
        if self.since is not None:
            points.add(self.since)
        for v in self.values:
            if v.since is not None:
                points.add(v.since)
            if v.until is not None:
                points.add(v.until)
        return frozenset(points)


@dataclass(frozen=True)
class FieldVersion:
    """One version of a field — its declared type tree over the half-open
    protocol range `[since, until)`. A field with a single, version-invariant
    shape has one entry; a redeclared field has one entry per declaration.
    """
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
        """Type tree of a single-version field. Caller asserts the field has one version."""
        (version,) = self.versions
        return version.type


@dataclass(frozen=True)
class Struct:
    name: str
    fields: tuple[Field, ...]
    nested_enums: tuple[Enum, ...]
    packet_id: int | None
    since: int | None = None

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset().union(
            *(
                version.type.referenced
                for f in self.fields
                for version in f.versions
                if version.type is not None
            )
        )

    @property
    def change_points(self) -> frozenset[int]:
        points: set[int] = set()
        if self.since is not None:
            points.add(self.since)
        for f in self.fields:
            for version in f.versions:
                if version.since is not None:
                    points.add(version.since)
                if version.until is not None:
                    points.add(version.until)
        return frozenset(points)


@dataclass(frozen=True)
class PrimitiveAlias:
    """`type Name = <primitive>`. Rendered as `enum Name : ctype {}` in C++:
    a distinct integer type wire-compatible with the underlying primitive,
    so a user may specialize `Serializer<Name>` apart from the primitive's."""
    name: str
    primitive: str


@dataclass(frozen=True)
class TypeAlias:
    """`type Name = <non-primitive>`. Rendered as `using Name = ctype` in
    C++; `target` is the single field-type tree."""
    name: str
    target: FieldType


@dataclass(frozen=True)
class File:
    """One `.py` file's contribution to the schema.

    `imports` carry dotted names of other loaded files this one draws types
    from. The resolver dereferences them against the surrounding
    `FileSet`.
    """
    name: str                                              # dotted module name
    stem: str                                              # output filename stem
    package: str | None                                    # output namespace
    enums: tuple[Enum, ...]
    structs: tuple[Struct, ...]
    primitive_aliases: tuple[PrimitiveAlias, ...]
    type_aliases: tuple[TypeAlias, ...]
    imports: tuple[str, ...]
    declaration_order: tuple[str, ...]                     # type names in source order


@dataclass(frozen=True)
class FileSet:
    """Every loaded file plus the subset marked for output.

    Analog of protoc's `DescriptorPool`, narrowed: we keep no cross-file
    resolution machinery beyond the import dependency graph.
    """
    files: Mapping[str, File]
    outputs: tuple[str, ...]
    builtins: frozenset[str]


# --- resolved descriptors (post-versioning) -----------------------------------


@dataclass(frozen=True)
class VersionSnapshot:
    """One version of a type. `lo` is `since` (inclusive), `hi` is
    `until` (exclusive); `hi=None` means "open-ended". `is_fresh` marks
    snapshots whose definition is a new shape rather than a re-use.
    """
    lo: int
    hi: int | None
    is_fresh: bool
    concrete: int                                          # snapshot where this shape was first emitted
    enum: Enum | None = None                               # narrowed view if this type is an enum
    struct: Struct | None = None                           # narrowed view if this type is a struct


@dataclass(frozen=True)
class ResolvedFile:
    """The post-resolver boundary delivered to backends.

    Carries everything the frontend has resolved on behalf of the backend:
    version snapshots, topological order, the FileSet for cross-file lookup.
    """
    file: File
    file_set: FileSet
    declaration_order: tuple[str, ...]                     # versioned topo order
    versioned_types: frozenset[str]
    snapshots: tuple[int, ...]                             # global snapshot points
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

    def is_versioned(self, name: str) -> bool:
        return name in self.versioned_types

    def snapshots_of(self, name: str) -> tuple[VersionSnapshot, ...]:
        return self.snapshots_by_type.get(name, ())

    def present_at(self, name: str, snapshot: int) -> VersionSnapshot | None:
        for s in self.snapshots_of(name):
            if s.lo == snapshot:
                return s
        return None

    def fresh_snapshots(self, name: str) -> tuple[VersionSnapshot, ...]:
        return tuple(s for s in self.snapshots_of(name) if s.is_fresh)
