"""Typed IR for parsed protocol modules.

A thin descriptor layer between griffe's AST and the Jinja templates: one
griffe walk produces fully-typed `ModuleDef` / `PacketDef` / `EnumDef` /
`FieldDef` values that downstream code reads via attribute access instead
of dict lookups.

The names mirror protobuf's descriptor model (`FileDescriptor` →
`DescriptorProto` → `FieldDescriptorProto`) so the intent is recognizable.
"""

from dataclasses import dataclass, replace
from enum import StrEnum, auto

import click
import griffe

from .parse import (
    class_packet_id,
    class_since,
    is_int_enum,
    name_kwarg,
    parse_member_value,
    since_kwarg,
)
from .types import WIRE_METHODS, resolve_type


class FieldKind(StrEnum):
    """How a field's bytes are written/read on the wire.

    Drives both the C++ in-memory type and the Serializer specialization
    template branch. `unknown` is the fallback when the annotation+marker
    pair doesn't match any supported shape yet.
    """

    ENUM = auto()
    STRUCT = auto()
    STRING = auto()
    OPTIONAL_VARIANT = auto()  # X | None with field(type=Union)
    UNKNOWN = auto()


@dataclass(frozen=True)
class WireMethods:
    """BinaryStream method names + the integer the serializer converts to/from."""

    write: str
    read: str
    underlying: str

    @classmethod
    def from_dict(cls, d: dict) -> "WireMethods":
        return cls(write=d["write"], read=d["read"], underlying=d["underlying"])


@dataclass(frozen=True)
class FieldDef:
    """An instance field on a packet/struct.

    `ctype` is the resolved C++ type (already routed through `ProtocolVersion`
    for user-defined types). `inner` is set only for `OPTIONAL_VARIANT` and
    describes the wrapped non-None branch — its `name` is unused.
    """

    name: str
    ctype: str
    since: int | None
    kind: FieldKind
    type_name: str | None = None  # for ENUM, STRUCT (the wrapper class name)
    inner: "FieldDef | None" = None  # for OPTIONAL_VARIANT


@dataclass(frozen=True)
class EnumMember:
    name: str
    value: int
    since: int | None


@dataclass(frozen=True)
class EnumDef:
    """An IntEnum class. `wire` is filled in if any field references this enum;
    otherwise `None` and no Serializer specialization is emitted."""

    name: str
    members: tuple[EnumMember, ...]
    since: int | None  # from @enum(since=N)
    wire: WireMethods | None = None


@dataclass(frozen=True)
class PacketDef:
    """A struct definition. `id` is set iff the class carries `@packet(id=N)`;
    plain structs (e.g. `DisconnectPacketMessages`) have `id=None`."""

    name: str
    id: int | None
    members: tuple[FieldDef, ...]


@dataclass(frozen=True)
class AliasDef:
    """A module-level type alias — both `type Name = ...` and `Name = ...`."""

    name: str
    ctype: str


Definition = PacketDef | EnumDef | AliasDef


@dataclass(frozen=True)
class ModuleDef:
    """One protocol source file's worth of definitions.

    `package` is the dotted namespace split on `.` — e.g. `bedrock.protocol`
    yields `["bedrock", "protocol"]`. Empty list means no namespace.

    `definitions` preserves the original source order across packets, enums,
    and aliases — the template emits them in the order they were declared.
    """

    package: list[str]
    definitions: tuple[Definition, ...]


def _build_field(
    name: str,
    attr,
    class_names: set[str],
    enum_names: set[str],
) -> FieldDef | None:
    """Resolve one instance attribute into a `FieldDef`. None if unmappable."""
    if attr.annotation is None:
        return None
    ctype = resolve_type(attr.annotation, class_names, enum_names)
    if ctype is None:
        return None
    since = since_kwarg(attr.value, "field") if attr.value is not None else None

    ann = attr.annotation
    # `X | None` — optional. Variant-wire (single-byte discriminator) iff the
    # field carries `field(type=Union)`; otherwise we still produce a kind
    # but mark it unknown so the template stops short of emitting a Serializer.
    if (
        isinstance(ann, griffe.ExprBinOp)
        and ann.operator == "|"
        and (ann.right == "None" or ann.left == "None")
    ):
        other = ann.left if ann.right == "None" else ann.right
        inner_kind = _direct_kind(other, class_names, enum_names)
        marker = name_kwarg(attr.value, "field", "type") if attr.value else None
        if inner_kind is None or marker != "Union":
            return FieldDef(name, ctype, since, FieldKind.UNKNOWN)
        return FieldDef(
            name,
            ctype,
            since,
            FieldKind.OPTIONAL_VARIANT,
            inner=FieldDef(
                name="",
                ctype="",  # not used; resolve_type handles the outer std::optional
                since=None,
                kind=inner_kind.kind,
                type_name=inner_kind.type_name,
            ),
        )

    direct = _direct_kind(ann, class_names, enum_names)
    if direct is None:
        return FieldDef(name, ctype, since, FieldKind.UNKNOWN)
    return FieldDef(name, ctype, since, direct.kind, type_name=direct.type_name)


@dataclass(frozen=True)
class _Kind:
    kind: FieldKind
    type_name: str | None = None


def _direct_kind(ann, class_names: set[str], enum_names: set[str]) -> _Kind | None:
    """Classify a non-optional annotation. None if unrecognized."""
    if isinstance(ann, griffe.ExprName):
        n = ann.name
        if n in enum_names:
            return _Kind(FieldKind.ENUM, n)
        if n in class_names:
            return _Kind(FieldKind.STRUCT, n)
        if n == "str":
            return _Kind(FieldKind.STRING)
    return None


def _build_packet(
    cls, class_names: set[str], enum_names: set[str]
) -> PacketDef | None:
    """Build a `PacketDef` from a non-enum class. None if any field unmappable."""
    members: list[FieldDef] = []
    for name, attr in cls.attributes.items():
        f = _build_field(name, attr, class_names, enum_names)
        if f is None:
            return None
        members.append(f)
    return PacketDef(name=cls.name, id=class_packet_id(cls), members=tuple(members))


def _build_enum(cls) -> EnumDef:
    members: list[EnumMember] = []
    for name, attr in cls.attributes.items():
        if attr.value is None:
            continue
        parsed = parse_member_value(attr.value)
        if parsed is None:
            continue
        ivalue, since = parsed
        members.append(EnumMember(name=name, value=ivalue, since=since))
    return EnumDef(
        name=cls.name,
        members=tuple(members),
        since=class_since(cls),
    )


def _collect_enum_wires(
    packets: tuple[PacketDef, ...],
    cls_by_name: dict[str, griffe.Class],
    enum_names: set[str],
) -> dict[str, WireMethods]:
    """Walk packet fields for `type=<primitive>` markers on enum-typed fields.

    Mirrors the old `enum_serializers` filter: enum-typed fields must carry
    `field(type=<primitive>)`, last write wins on conflict.
    """
    out: dict[str, WireMethods] = {}
    for pkt in packets:
        cls = cls_by_name[pkt.name]
        for fname, attr in cls.attributes.items():
            if not isinstance(attr.annotation, griffe.ExprName):
                continue
            type_name = attr.annotation.name
            if type_name not in enum_names:
                continue
            wire = name_kwarg(attr.value, "field", "type")
            if wire is None:
                raise click.ClickException(
                    f"{cls.name}.{fname}: enum-typed field requires "
                    f"field(type=<primitive>) — e.g. type=uvarint32"
                )
            if wire not in WIRE_METHODS:
                raise click.ClickException(
                    f"{cls.name}.{fname}: unknown wire primitive {wire!r}; "
                    f"valid: {sorted(WIRE_METHODS)}"
                )
            out[type_name] = WireMethods.from_dict(WIRE_METHODS[wire])
    return out


def _build_alias(member, class_names: set[str], enum_names: set[str]) -> AliasDef | None:
    """Resolve a module-level alias (plain assignment or PEP 695 `type` stmt)."""
    if member.value is None:
        return None
    ctype = resolve_type(member.value, class_names, enum_names)
    if ctype is None:
        return None
    return AliasDef(name=member.name, ctype=ctype)


def build_module(mod) -> ModuleDef:
    """Single pass: griffe module → typed IR, preserving source order."""
    classes = [c for c in mod.classes.values() if not c.is_alias]
    class_names = {c.name for c in classes}
    enum_names = {c.name for c in classes if is_int_enum(c)}

    # First pass: build packets so we can collect the enum wires they imply.
    cls_by_name = {c.name: c for c in classes}
    packets_by_name: dict[str, PacketDef] = {}
    for c in classes:
        if is_int_enum(c):
            continue
        pkt = _build_packet(c, class_names, enum_names)
        if pkt is not None:
            packets_by_name[c.name] = pkt

    wires = _collect_enum_wires(
        tuple(packets_by_name.values()), cls_by_name, enum_names
    )

    # Second pass: walk `mod.members` in declaration order, dispatching each.
    definitions: list[Definition] = []
    for name, member in mod.members.items():
        if name == "package":
            continue
        if name in packets_by_name:
            definitions.append(packets_by_name[name])
        elif name in cls_by_name and is_int_enum(cls_by_name[name]):
            definitions.append(replace(_build_enum(cls_by_name[name]), wire=wires.get(name)))
        elif isinstance(member, (griffe.Attribute, griffe.TypeAlias)):
            alias = _build_alias(member, class_names, enum_names)
            if alias is not None:
                definitions.append(alias)

    pkg_attr = mod.members.get("package")
    package_str = (
        str(pkg_attr.value).strip("'\"") if pkg_attr and pkg_attr.value else ""
    )
    package = package_str.split(".") if package_str else []

    return ModuleDef(package=package, definitions=tuple(definitions))
