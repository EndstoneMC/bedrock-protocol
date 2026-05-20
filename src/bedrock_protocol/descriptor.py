"""Bedrock-protocol IR — the language-agnostic boundary between frontend and backend.

This module is the analog of protoc's `descriptor.{h,cc}`. The frontend
(`compiler.parser`) produces a `FileDescriptor`; the resolver
(`compiler.resolver`) refines it into a `ResolvedFileDescriptor`, which is
the only descriptor type a backend receives.

Every dataclass here is frozen and read-only. A backend that wants to know
"what is this type's shape" reads `TypeRef`; a backend that wants to know
"how does this travel on the wire" reads `Wire`. The split is deliberate —
the C++ backend spells `std::optional<X>` from the `TypeRef` but emits a
one-byte presence flag from the `Wire`, and a future Python backend would
make different choices on both.
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


# --- declared shape (TypeRef) -------------------------------------------------


@dataclass(frozen=True)
class PrimitiveRef:
    kind: Literal["primitive"] = "primitive"
    name: str = ""

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset()


@dataclass(frozen=True)
class NamedRef:
    """Reference to a user-defined enum, struct, or alias."""
    name: str
    kind: Literal["named"] = "named"

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset({self.name})


@dataclass(frozen=True)
class OptionalRef:
    inner: "TypeRef"
    kind: Literal["optional"] = "optional"

    @property
    def referenced(self) -> frozenset[str]:
        return self.inner.referenced


@dataclass(frozen=True)
class RepeatedRef:
    """`list[T]` when `count` is None, `tuple[T, ..., T]` when set."""
    inner: "TypeRef"
    count: int | None
    kind: Literal["repeated"] = "repeated"

    @property
    def referenced(self) -> frozenset[str]:
        return self.inner.referenced


@dataclass(frozen=True)
class MappingRef:
    key: "TypeRef"
    value: "TypeRef"
    kind: Literal["mapping"] = "mapping"

    @property
    def referenced(self) -> frozenset[str]:
        return self.key.referenced | self.value.referenced


@dataclass(frozen=True)
class VariantRef:
    """`std::variant`-shaped tagged union. A None arm is `std::monostate`."""
    arms: tuple["TypeRef | None", ...]
    kind: Literal["variant"] = "variant"

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset().union(
            *(a.referenced for a in self.arms if a is not None)
        )


TypeRef = PrimitiveRef | NamedRef | OptionalRef | RepeatedRef | MappingRef | VariantRef


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


# --- on-the-wire encoding (Wire) ---------------------------------------------


@dataclass(frozen=True)
class ScalarWire:
    primitive: str
    varint: bool
    big_endian: bool = False
    kind: Literal["scalar"] = "scalar"


@dataclass(frozen=True)
class StringWire:
    """A varuint32 length prefix followed by raw bytes."""
    kind: Literal["string"] = "string"


@dataclass(frozen=True)
class StructWire:
    name: str
    kind: Literal["struct"] = "struct"


@dataclass(frozen=True)
class EnumWire:
    """`scalar` None → name-coded; set → integer-coded over that scalar."""
    name: str
    scalar: ScalarWire | None
    kind: Literal["enum"] = "enum"


@dataclass(frozen=True)
class OptionalWire:
    """`discriminator` False → one-byte bool flag; True → varuint union tag.

    With a union tag, `present_tag` is the tag value that means "payload
    follows" (0 for `T | None`, 1 for `None | T`).
    """
    inner: "Wire"
    discriminator: bool
    present_tag: int = 0
    kind: Literal["optional"] = "optional"


@dataclass(frozen=True)
class RepeatedWire:
    inner: "Wire"
    prefix: ScalarWire | None
    count: int | None
    kind: Literal["repeated"] = "repeated"


@dataclass(frozen=True)
class MappingWire:
    key: "Wire"
    value: "Wire"
    prefix: ScalarWire
    kind: Literal["mapping"] = "mapping"


@dataclass(frozen=True)
class SwitchWire:
    """varuint32-tagged union. A None arm carries no payload."""
    arms: tuple["Wire | None", ...]
    kind: Literal["switch"] = "switch"


@dataclass(frozen=True)
class CondWire:
    """Field present only when `predicate` holds against earlier fields.
    No presence marker on the wire — both sides recompute it.

    `group` is the index of the `with field(when=...)` block the field came
    from; fields sharing it form one guarded region. None is a lone
    `field(when=)`.
    """
    inner: "Wire"
    predicate: Predicate
    group: int | None = None
    kind: Literal["cond"] = "cond"


Wire = (
    ScalarWire | StringWire | StructWire | EnumWire | OptionalWire
    | RepeatedWire | MappingWire | SwitchWire | CondWire
)


# --- declarations ------------------------------------------------------------


@dataclass(frozen=True)
class EnumValueDescriptor:
    name: str
    number: int
    since: int | None
    until: int | None

    @property
    def wire_name(self) -> str:
        """The string a name-coded enum puts on the wire."""
        return self.name.lower().replace("_", "")


@dataclass(frozen=True)
class EnumDescriptor:
    name: str
    values: tuple[EnumValueDescriptor, ...]
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
class FieldEraDescriptor:
    """One version era of a field — its declared shape and wire encoding
    over the half-open protocol range `[since, until)`. A field with a
    single, version-invariant shape has one era; one redeclared per era
    has one entry per declaration.
    """
    type_ref: TypeRef | None
    wire: Wire | None
    since: int | None
    until: int | None


@dataclass(frozen=True)
class FieldDescriptor:
    name: str
    eras: tuple[FieldEraDescriptor, ...]

    def era_at(self, snapshot: int) -> FieldEraDescriptor | None:
        for era in self.eras:
            lo = era.since or 0
            if lo <= snapshot and (era.until is None or snapshot < era.until):
                return era
        return None

    def present_at(self, snapshot: int) -> bool:
        return self.era_at(snapshot) is not None

    @property
    def type_ref_single(self) -> TypeRef | None:
        """Declared shape of a single-era field. Caller asserts the field has one era."""
        (era,) = self.eras
        return era.type_ref

    @property
    def wire_single(self) -> Wire | None:
        """Wire encoding of a single-era field. Caller asserts the field has one era."""
        (era,) = self.eras
        return era.wire


@dataclass(frozen=True)
class StructDescriptor:
    name: str
    fields: tuple[FieldDescriptor, ...]
    nested_enums: tuple[EnumDescriptor, ...]
    packet_id: int | None
    since: int | None = None

    @property
    def referenced(self) -> frozenset[str]:
        return frozenset().union(
            *(
                era.type_ref.referenced
                for f in self.fields
                for era in f.eras
                if era.type_ref is not None
            )
        )

    @property
    def change_points(self) -> frozenset[int]:
        points: set[int] = set()
        if self.since is not None:
            points.add(self.since)
        for f in self.fields:
            for era in f.eras:
                if era.since is not None:
                    points.add(era.since)
                if era.until is not None:
                    points.add(era.until)
        return frozenset(points)


@dataclass(frozen=True)
class PrimitiveAliasDescriptor:
    """`type Name = <primitive>`. Rendered as `enum Name : ctype {}` in C++:
    a distinct integer type wire-compatible with the underlying primitive,
    so a user may specialize `Serializer<Name>` apart from the primitive's."""
    name: str
    primitive: str


@dataclass(frozen=True)
class TypeAliasDescriptor:
    """`type Name = <non-primitive>`. Rendered as `using Name = ctype` in
    C++; `target` is the declared shape and `wire` its encoding."""
    name: str
    target: TypeRef
    wire: Wire


@dataclass(frozen=True)
class FileDescriptor:
    """One `.py` file's contribution to the schema.

    `imports` carry dotted names of other loaded files this one draws types
    from. The resolver dereferences them against the surrounding
    `FileSet`.
    """
    name: str                                              # dotted module name
    stem: str                                              # output filename stem
    package: str | None                                    # output namespace
    enums: tuple[EnumDescriptor, ...]
    structs: tuple[StructDescriptor, ...]
    primitive_aliases: tuple[PrimitiveAliasDescriptor, ...]
    type_aliases: tuple[TypeAliasDescriptor, ...]
    imports: tuple[str, ...]
    declaration_order: tuple[str, ...]                     # type names in source order


@dataclass(frozen=True)
class FileSet:
    """Every loaded file plus the subset marked for output.

    Analog of protoc's `DescriptorPool`, narrowed: we keep no cross-file
    resolution machinery beyond the import dependency graph.
    """
    files: Mapping[str, FileDescriptor]
    outputs: tuple[str, ...]
    builtins: frozenset[str]


# --- resolved descriptors (post-versioning) -----------------------------------


@dataclass(frozen=True)
class VersionSnapshot:
    """One version era of a type. `lo` is `since` (inclusive), `hi` is
    `until` (exclusive); `hi=None` means "open-ended". `is_fresh` marks
    snapshots whose definition is a new shape rather than a re-use.
    """
    lo: int
    hi: int | None
    is_fresh: bool
    concrete: int                                          # snapshot where this shape was first emitted
    enum: EnumDescriptor | None = None                     # narrowed view if this type is an enum
    struct: StructDescriptor | None = None                 # narrowed view if this type is a struct


@dataclass(frozen=True)
class ResolvedFileDescriptor:
    """The post-resolver boundary delivered to backends.

    Carries everything the frontend has resolved on behalf of the backend:
    version snapshots, topological order, the FileSet for cross-file lookup.
    """
    file: FileDescriptor
    file_set: FileSet
    declaration_order: tuple[str, ...]                     # versioned topo order
    versioned_types: frozenset[str]
    snapshots: tuple[int, ...]                             # global snapshot points
    snapshots_by_type: Mapping[str, tuple[VersionSnapshot, ...]]

    def lookup(self, name: str) -> EnumDescriptor | StructDescriptor | None:
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
