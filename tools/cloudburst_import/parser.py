"""javalang wrappers that extract just the bits we care about.

We don't try to model the full Java AST. We pull out:
- packet class field declarations (name + Java type + optional @since Javadoc)
- serializer class metadata (extends chain, serialize() method body)
- Bedrock_vNNN registerPacket/updateSerializer/deregisterPacket calls
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import javalang
from javalang.tree import (
    ClassCreator,
    ClassDeclaration,
    ClassReference,
    CompilationUnit,
    FieldDeclaration,
    Literal,
    MemberReference,
    MethodDeclaration,
    MethodInvocation,
    MethodReference,
    ReferenceType,
)


@dataclass
class PacketField:
    """A `private T name;` declaration on a packet class."""

    name: str
    java_type: str
    since: int | None = None


@dataclass
class PacketClass:
    """A `*Packet.java` file: ordered fields + class-level metadata."""

    name: str
    fields: list[PacketField] = field(default_factory=list)
    extends: str | None = None


@dataclass
class Serializer:
    """A `*Serializer_vNNN.java` file: extends chain + serialize() body."""

    name: str
    version: int
    packet_class: str
    extends: str | None
    serialize_body: list  # list[javalang.tree.Statement]


@dataclass
class CodecRegistration:
    """One call in a Bedrock_vNNN builder chain."""

    kind: str  # "register" | "update" | "deregister"
    packet_class: str
    serializer_class: str | None  # None for deregister
    packet_id: int | None  # only for register


def parse_file(path: Path) -> CompilationUnit:
    """Parse a Java source file, returning the javalang CompilationUnit."""
    return javalang.parse.parse(path.read_text(encoding="utf-8"))


def parse_packet_class(path: Path) -> PacketClass:
    """Extract field declarations from a `*Packet.java` source file."""
    tree = parse_file(path)
    cls: ClassDeclaration | None = None
    for type_decl in tree.types:
        if isinstance(type_decl, ClassDeclaration):
            cls = type_decl
            break
    if cls is None:
        raise ValueError(f"no class declaration in {path}")

    pkt = PacketClass(name=cls.name, extends=cls.extends.name if cls.extends else None)
    for member in cls.body:
        if not isinstance(member, FieldDeclaration):
            continue
        modifiers = set(member.modifiers or ())
        if "static" in modifiers:
            continue
        java_type = _render_type(member.type)
        for decl in member.declarators:
            pkt.fields.append(
                PacketField(
                    name=decl.name,
                    java_type=java_type,
                    since=_extract_since(member.documentation),
                )
            )
    return pkt


_SERIALIZER_NAME_RE = re.compile(r"^([A-Za-z0-9_]+)Serializer_v(\d+)$")


def parse_serializer(path: Path) -> Serializer | None:
    """Extract a `*Serializer_vNNN.java` source file.

    Returns None when the file is not a packet serializer (e.g. helper-only).
    """
    tree = parse_file(path)
    cls: ClassDeclaration | None = None
    for type_decl in tree.types:
        if isinstance(type_decl, ClassDeclaration):
            cls = type_decl
            break
    if cls is None:
        return None

    m = _SERIALIZER_NAME_RE.match(cls.name)
    if not m:
        return None
    packet_name = m.group(1) + "Packet"
    version = int(m.group(2))

    serialize_body: list = []
    for member in cls.body:
        if isinstance(member, MethodDeclaration) and member.name == "serialize":
            serialize_body = member.body or []
            break

    return Serializer(
        name=cls.name,
        version=version,
        packet_class=packet_name,
        extends=cls.extends.name if cls.extends else None,
        serialize_body=serialize_body,
    )


def parse_codec_registrations(path: Path) -> list[CodecRegistration]:
    """Walk `Bedrock_vNNN.java` for builder calls in source order.

    Captures:
      .registerPacket(Pkt::new, Ser.INSTANCE, <id>, ...) -> kind="register"
      .updateSerializer(Pkt.class, Ser.INSTANCE | new Ser(...)) -> kind="update"
      .deregisterPacket(Pkt.class)                       -> kind="deregister"

    Source order matters: a later call in the same file overrides earlier ones.
    """
    tree = parse_file(path)
    regs: list[CodecRegistration] = []
    seen: set[int] = set()  # de-dup the same call surfaced via multiple AST paths

    for _, item in tree:
        if not isinstance(item, MethodInvocation):
            continue
        if id(item) in seen:
            continue
        name = item.member
        if name == "registerPacket":
            reg = _parse_register(item)
        elif name == "updateSerializer":
            reg = _parse_update(item)
        elif name == "deregisterPacket":
            reg = _parse_deregister(item)
        else:
            continue
        if reg is not None:
            seen.add(id(item))
            regs.append(reg)
    return regs


def _parse_register(inv: MethodInvocation) -> CodecRegistration | None:
    args = inv.arguments
    if len(args) < 3:
        return None
    pkt_cls = _method_ref_target(args[0])
    ser_cls = _instance_field_holder(args[1])
    pkt_id = _literal_int(args[2])
    if pkt_cls is None or pkt_id is None:
        return None
    return CodecRegistration("register", pkt_cls, ser_cls, pkt_id)


def _parse_update(inv: MethodInvocation) -> CodecRegistration | None:
    args = inv.arguments
    if len(args) < 2:
        return None
    pkt_cls = _class_literal_target(args[0])
    ser_cls = _instance_field_holder(args[1]) or _ctor_target(args[1])
    if pkt_cls is None:
        return None
    return CodecRegistration("update", pkt_cls, ser_cls, None)


def _parse_deregister(inv: MethodInvocation) -> CodecRegistration | None:
    args = inv.arguments
    if not args:
        return None
    pkt_cls = _class_literal_target(args[0])
    if pkt_cls is None:
        return None
    return CodecRegistration("deregister", pkt_cls, None, None)


def _render_type(t) -> str:
    if t is None:
        return "void"
    if isinstance(t, ReferenceType):
        name = t.name
        if t.arguments:
            inner = ", ".join(_render_type(a.type) if hasattr(a, "type") and a.type else "?" for a in t.arguments)
            name = f"{name}<{inner}>"
        if t.dimensions:
            name += "[]" * len(t.dimensions)
        return name
    name = getattr(t, "name", None) or type(t).__name__
    dims = getattr(t, "dimensions", None) or []
    return name + "[]" * len(dims)


_SINCE_RE = re.compile(r"@since\s+v?(\d+)")


def _extract_since(doc: str | None) -> int | None:
    if not doc:
        return None
    m = _SINCE_RE.search(doc)
    return int(m.group(1)) if m else None


def _method_ref_target(arg) -> str | None:
    """Pkt::new -> 'Pkt'."""
    if not isinstance(arg, MethodReference):
        return None
    expr = arg.expression
    if isinstance(expr, MemberReference):
        return expr.member
    return None


def _instance_field_holder(arg) -> str | None:
    """Ser.INSTANCE -> 'Ser'."""
    if not isinstance(arg, MemberReference):
        return None
    if arg.member == "INSTANCE" and arg.qualifier:
        return arg.qualifier
    return None


def _class_literal_target(arg) -> str | None:
    """Pkt.class -> 'Pkt'."""
    if isinstance(arg, ClassReference):
        t = arg.type
        if isinstance(t, ReferenceType):
            return t.name
    return None


def _ctor_target(arg) -> str | None:
    """new Foo(...) -> 'Foo'."""
    if isinstance(arg, ClassCreator):
        t = arg.type
        if isinstance(t, ReferenceType):
            return t.name
    return None


def _literal_int(arg) -> int | None:
    if not isinstance(arg, Literal):
        return None
    val = arg.value
    if isinstance(val, str):
        try:
            return int(val, 0)
        except ValueError:
            return None
    return None
