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

from dataclasses import dataclass, field
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

    `trailing` flips a `bytes` field from "length-prefixed" to "consume the
    remaining unread bytes in the frame" -- the wire form has no length
    marker, and the frame boundary terminates the read. Only valid for
    `bytes`, and only when the field is the last one in its struct.
    """
    name: str
    big_endian: bool = False
    alias: str | None = None
    trailing: bool = False
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
    """`list[T]` when `count` and `count_expr` are None and `prefix` carries
    the length wire; `tuple[T, ..., T]` when `count` is set and `prefix` is
    None (fixed array); `list[T]` with `count_expr` set when the element
    count is computed at serialize/deserialize time from earlier fields
    (`count=lambda p: ...`), again carrying no wire prefix."""
    inner: "FieldType"
    count: int | None = None
    count_expr: "Predicate | None" = None
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
    """`std::variant`-shaped tagged union. `discriminator` is the integer
    primitive that prefixes the active case index on the wire (default
    `uvarint32`); a `None` case carries no payload (`std::monostate` in C++).
    `tag_enum` names a user-defined `IntEnum` whose members supply the C++
    case labels (`EnumName::MEMBER`) one-to-one with the variant alternatives,
    in declaration order; the wire form remains `discriminator`."""
    cases: tuple["FieldType | None", ...]
    discriminator: PrimitiveType = field(
        default_factory=lambda: PrimitiveType(name="uvarint32")
    )
    tag_enum: str | None = None
    kind: Literal["variant"] = "variant"

    @property
    def referenced(self) -> frozenset[str]:
        refs = frozenset().union(
            *(a.referenced for a in self.cases if a is not None)
        )
        if self.tag_enum is not None:
            refs = refs | frozenset({self.tag_enum})
        return refs


@dataclass(frozen=True)
class BitsetType:
    """A fixed-size `std::bitset<N>` on the wire. Serialized as a base-128
    little-endian dump of the bitset's numeric value: seven payload bits per
    byte, the top bit a continuation flag, with a single 0x00 byte for the
    empty bitset.

    `size` is the literal width baked into the generated `std::bitset<N>`.
    `enum_member` records a symbolic `(enum_name, member_name)` ref when the
    DSL spelled the width as `bitset[Enum.MEMBER]`. The resolver narrows that
    ref against each snapshot's nested-enum view, so per-version sentinels
    yield per-version bitset widths.
    """
    size: int
    enum_member: tuple[str, str] | None = None
    kind: Literal["bitset"] = "bitset"

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset()


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
    | MappingType | VariantType | BitsetType | CondType
)


# --- declarations ------------------------------------------------------------


@dataclass(frozen=True)
class EnumValue:
    name: str
    number: int
    since: int | None
    until: int | None
    deprecated: int | None = None
    sentinel: bool = False

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
            if v.deprecated is not None:
                points.add(v.deprecated)
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
    deprecated: int | None = None
    nested_structs: tuple["Struct", ...] = ()

    @property
    def referenced(self) -> frozenset[str]:
        own = frozenset().union(
            *(
                version.type.referenced
                for f in self.fields
                for version in f.versions
                if version.type is not None
            )
        )
        # Nested structs may reference other module-scope types -- a field on
        # `BookEditAction.ReplacePage` of type `Vec3` should pull `Vec3` into
        # the parent's reference set so cross-file imports and topological
        # ordering work the same as a non-nested field would.
        for ns in self.nested_structs:
            own = own | ns.referenced
        return own

    @property
    def change_points(self) -> frozenset[int]:
        points: set[int] = set()
        if self.since is not None:
            points.add(self.since)
        if self.deprecated is not None:
            points.add(self.deprecated)
        for f in self.fields:
            for version in f.versions:
                if version.since is not None:
                    points.add(version.since)
                if version.until is not None:
                    points.add(version.until)
        for e in self.nested_enums:
            points |= e.change_points
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


@dataclass
class FileSet:
    """Every loaded file plus the subset marked for output.

    Analog of protoc's `DescriptorPool`, narrowed: we keep no cross-file
    resolution machinery beyond the import dependency graph and a memo of
    each file's `ResolvedFile` once it has been processed.
    """
    files: Mapping[str, File]
    outputs: tuple[str, ...]
    builtins: frozenset[str]
    version: int | None = None
    resolved: dict[str, "ResolvedFile"] = field(default_factory=dict)


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
        if name in self.versioned_types:
            return True
        for imp in self.file.imports:
            other = self.file_set.resolved.get(imp)
            if other is not None and other.is_versioned(name):
                return True
        return False

    def snapshots_of(self, name: str) -> tuple[VersionSnapshot, ...]:
        own = self.snapshots_by_type.get(name)
        if own is not None:
            return own
        for imp in self.file.imports:
            other = self.file_set.resolved.get(imp)
            if other is None:
                continue
            snaps = other.snapshots_of(name)
            if snaps:
                return snaps
        return ()

    def present_at(self, name: str, snapshot: int) -> VersionSnapshot | None:
        # Exact-boundary match first -- that's what intra-file callers iterate.
        # Cross-file consumers may ask about a snapshot that isn't a boundary
        # in the producer file (e.g. PAIP at v388 referencing an inventory
        # type whose own boundaries are {0, 685, 944}); fall through to a
        # range lookup so they get the snapshot whose `[lo, hi)` covers it.
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
