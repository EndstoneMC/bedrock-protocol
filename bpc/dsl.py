"""Bedrock-Protocol Python DSL — schema and AST-based parser.

A packet definition file is plain Python::

    from typing import ClassVar

    class DisconnectPacket:
        id: ClassVar[int] = 5
        reason: DisconnectFailReason
        messages: DisconnectPacketMessages | None

We do not import packet files — we parse them as syntax. That lets the user
reference C++ types (``DisconnectFailReason``, ``DisconnectPacketMessages``)
that are never defined in Python, the same way ``protoc`` resolves message
names by string.

Interpretation rules:
    * Class with ``id: ClassVar[int] = N`` is a packet. ``ClassVar`` marks the
      attribute as packet-level metadata, not a wire field.
    * Annotation that is a bare name in :data:`PRIMITIVE_TYPES` → primitive.
    * Annotation that is any other bare name → enum-typed field; the wire
      discriminator defaults to ``uvarint32``.
    * Annotation written as ``A | B | None`` → switch / tagged-union; each
      operand is a struct case, ``None`` is the empty case
      (``std::monostate``); discriminator defaults to ``uvarint32``.
"""

import ast
from dataclasses import dataclass
from dataclasses import field as _field
from pathlib import Path
from typing import List, Optional, Union

PRIMITIVE_TYPES = {
    "u8",
    "i8",
    "u16",
    "i16",
    "u32",
    "i32",
    "u64",
    "i64",
    "uvarint32",
    "varint32",
    "uvarint64",
    "varint64",
    "string",
    "bool",
    "float",
    "double",
}


@dataclass
class PrimitiveType:
    name: str


@dataclass
class NamedType:
    """A user-named type — an enum in bare position, a struct in a switch case."""

    name: str


@dataclass
class SwitchType:
    cases: List[Optional[Union[PrimitiveType, NamedType]]] = _field(
        default_factory=list
    )
    discriminator: str = "uvarint32"


Type = Union[PrimitiveType, NamedType, SwitchType]


@dataclass
class FieldDef:
    name: str
    type: Type


@dataclass
class PacketDef:
    name: str
    id: int
    fields: List[FieldDef] = _field(default_factory=list)


def parse_file(path: Path) -> List[PacketDef]:
    """Parse a packet definition file. Returns every packet class found."""
    tree = ast.parse(path.read_text(), filename=str(path))
    packets = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            pkt = _parse_class(node)
            if pkt is not None:
                packets.append(pkt)
    return packets


def _parse_class(node: ast.ClassDef) -> Optional[PacketDef]:
    pkt_id: Optional[int] = None
    fields: List[FieldDef] = []
    for stmt in node.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            if _is_classvar(stmt.annotation):
                # ClassVar marks packet-level metadata, never a wire field.
                if (
                    stmt.target.id == "id"
                    and isinstance(stmt.value, ast.Constant)
                    and isinstance(stmt.value.value, int)
                ):
                    pkt_id = stmt.value.value
                continue
            fields.append(
                FieldDef(name=stmt.target.id, type=_parse_annotation(stmt.annotation))
            )
    if pkt_id is None:
        return None
    return PacketDef(name=node.name, id=pkt_id, fields=fields)


def _is_classvar(annotation: ast.expr) -> bool:
    """True if ``annotation`` is ``ClassVar`` or ``ClassVar[...]`` (also as ``typing.ClassVar``)."""
    target = annotation
    if isinstance(annotation, ast.Subscript):
        target = annotation.value
    if isinstance(target, ast.Name):
        return target.id == "ClassVar"
    if isinstance(target, ast.Attribute):
        return target.attr == "ClassVar"
    return False


def _parse_annotation(node: ast.expr) -> Type:
    if isinstance(node, ast.Name):
        if node.id in PRIMITIVE_TYPES:
            return PrimitiveType(node.id)
        return NamedType(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        cases: List[Optional[Union[PrimitiveType, NamedType]]] = []
        _flatten_union(node, cases)
        return SwitchType(cases=cases)
    raise ValueError(f"unsupported annotation: {ast.dump(node)}")


def _flatten_union(node: ast.expr, out: list) -> None:
    """Flatten left-associative ``A | B | C`` into a list of cases."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        _flatten_union(node.left, out)
        _flatten_union(node.right, out)
        return
    if isinstance(node, ast.Constant) and node.value is None:
        out.append(None)
        return
    out.append(_parse_annotation(node))
