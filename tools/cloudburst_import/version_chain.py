"""Discover serializer chains and derive per-field since/until.

A packet's wire shape is the union of all `serialize()` bodies along its
inheritance chain. Each chain link is one version's serializer extending the
previous version's serializer. A field that first appears in the v712 link is
`since=712`; one that disappears at v975 is `until=975`.

The walker is per-packet — we don't try to globally diff every serializer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .parser import (
    CodecRegistration,
    Serializer,
    parse_codec_registrations,
    parse_serializer,
)

CLOUDBURST_FLOOR = 291  # CLAUDE.md rule 7 - v291 is a floor, not a since= point


@dataclass
class PacketInfo:
    """Per-packet registry data merged across all Bedrock_vNNN files."""

    name: str  # packet class name, e.g. "DisconnectPacket"
    packet_id: int
    since: int  # version of the Bedrock_vNNN that first .registerPacket()'d it
    until: int | None  # version of the Bedrock_vNNN that .deregisterPacket()'d it


@dataclass
class ChainLink:
    """One serializer in a packet's inheritance chain."""

    serializer: Serializer
    version: int  # parsed out of the file name


def discover_versions(cloudburst_root: Path) -> list[int]:
    """List `vNNN` codec directories under bedrock-codec/, sorted ascending."""
    base = _codec_root(cloudburst_root)
    versions: list[int] = []
    for child in base.iterdir():
        if not child.is_dir():
            continue
        m = re.match(r"^v(\d+)$", child.name)
        if m:
            versions.append(int(m.group(1)))
    versions.sort()
    return versions


def build_packet_registry(cloudburst_root: Path) -> dict[str, PacketInfo]:
    """Walk every Bedrock_vNNN.java for registration calls, in version order.

    For each packet:
    - `since` = the first version that .registerPacket()'d it.
    - `packet_id` = the id from that initial registration.
    - `until` = the version that .deregisterPacket()'d it, if any.

    Mid-life re-registrations with a different id are not handled; CloudburstMC
    doesn't actually do that for any packet, so we ignore the case.
    """
    base = _codec_root(cloudburst_root)
    registry: dict[str, PacketInfo] = {}

    for v in discover_versions(cloudburst_root):
        codec_file = base / f"v{v}" / f"Bedrock_v{v}.java"
        if not codec_file.exists():
            continue
        regs = parse_codec_registrations(codec_file)
        for reg in regs:
            if reg.kind == "register":
                if reg.packet_class not in registry and reg.packet_id is not None:
                    registry[reg.packet_class] = PacketInfo(
                        name=reg.packet_class,
                        packet_id=reg.packet_id,
                        since=v,
                        until=None,
                    )
            elif reg.kind == "deregister":
                info = registry.get(reg.packet_class)
                if info is not None and info.until is None:
                    info.until = v
    return registry


def find_serializer_chain(cloudburst_root: Path, packet_name: str) -> list[ChainLink]:
    """Locate every `<Name>Serializer_v*.java` and walk the extends chain.

    Returns links in ascending version order. The oldest link's `extends` will
    typically be `BedrockPacketSerializer<Pkt>` (the interface), which we
    represent by leaving its `serializer.extends` populated as-is — callers
    differentiate by checking version numbers, not the extends string.
    """
    if not packet_name.endswith("Packet"):
        raise ValueError(f"expected a *Packet class name, got {packet_name!r}")
    base_name = packet_name[: -len("Packet")]

    base = _codec_root(cloudburst_root)
    links: list[ChainLink] = []
    for v in discover_versions(cloudburst_root):
        candidate = base / f"v{v}" / "serializer" / f"{base_name}Serializer_v{v}.java"
        if not candidate.exists():
            continue
        ser = parse_serializer(candidate)
        if ser is None:
            continue
        # A serializer that overrides only helper methods (e.g. LoginSerializer_v818
        # overriding writeAuthJwt) does not change wire shape. Skip it.
        if not ser.serialize_body:
            continue
        links.append(ChainLink(serializer=ser, version=v))
    return links


@dataclass
class FieldOp:
    """A single statement in a serialize() body, normalized for diffing."""

    raw: object  # the javalang Statement node, retained for emit
    signature: str  # normalized text-ish key used for diff equality


@dataclass
class VersionedFieldOp(FieldOp):
    """A FieldOp annotated with the version interval it covers."""

    since: int | None  # None = present from the chain's first link
    until: int | None  # None = present through the chain's last link


def derive_field_history(chain: list[ChainLink]) -> list[VersionedFieldOp]:
    """Walk the chain, comparing each link's serialize() body to its parent's.

    Strategy (simple, good enough for drafts):
      - Pull each link's body as a list of FieldOps keyed by `signature`.
      - The newest link's body is the canonical shape.
      - For each op in the newest link, find the earliest link where that
        signature first appears -> that's its `since` (with v291-floor rule).
      - For an op that exists in older links but disappears in newer ones,
        attach `until` = first link where it's absent.

    The signature is a coarse pretty-print of the statement (see _signature).
    Order of ops within a body is preserved by relying on the newest link's
    list order — we don't try to merge interleavings across versions.
    """
    if not chain:
        return []

    # Inline super.serialize(...) calls by splicing in the parent link's body
    # at that point. Without this, v622 looks like it only writes `reason`,
    # when in fact `super.serialize(...)` inlines all of v291's writes.
    inlined: list[list] = []
    for i, link in enumerate(chain):
        inlined.append(_inline_super(link.serializer.serialize_body, inlined[:i]))
    bodies = [_body_to_ops(body) for body in inlined]

    newest = bodies[-1]
    versioned: list[VersionedFieldOp] = []
    for op in newest:
        first_seen = _first_seen(chain, bodies, op.signature)
        since_val: int | None
        if first_seen is None:
            since_val = chain[-1].version
        else:
            since_val = first_seen if first_seen > CLOUDBURST_FLOOR else None
        versioned.append(
            VersionedFieldOp(
                raw=op.raw,
                signature=op.signature,
                since=since_val,
                until=None,
            )
        )

    # Detect dropped fields: anything in an older body that is *not* in newer
    # bodies. We surface these only when the drop happened before the newest
    # link, so the reader still sees them with an `until=` marker.
    seen_in_newer: set[str] = {op.signature for op in newest}
    for i, body in enumerate(bodies[:-1]):
        for op in body:
            if op.signature in seen_in_newer:
                continue
            # Find first body where it disappears.
            drop_at: int | None = None
            for j in range(i + 1, len(chain)):
                if op.signature not in {o.signature for o in bodies[j]}:
                    drop_at = chain[j].version
                    break
            if drop_at is None:
                continue
            first_seen = _first_seen(chain[: i + 1], bodies[: i + 1], op.signature)
            since_val = first_seen if first_seen and first_seen > CLOUDBURST_FLOOR else None
            versioned.append(
                VersionedFieldOp(
                    raw=op.raw,
                    signature=op.signature,
                    since=since_val,
                    until=drop_at,
                )
            )
            seen_in_newer.add(op.signature)  # avoid duplicate emission
    return versioned


def _first_seen(
    chain: list[ChainLink],
    bodies: list[list[FieldOp]],
    signature: str,
) -> int | None:
    for link, body in zip(chain, bodies):
        if any(op.signature == signature for op in body):
            return link.version
    return None


def _inline_super(body: list, prior_bodies: list[list]) -> list:
    """Replace `super.serialize(...)` statements with the latest parent body.

    `prior_bodies` is the inlined bodies of older links in order. Java
    inheritance gives the immediate parent, but for our coarse purposes the
    most recent prior link is close enough — CloudburstMC serializers do not
    skip levels in practice.
    """
    from javalang.tree import StatementExpression, SuperMethodInvocation

    if not prior_bodies:
        return list(body)
    parent_body = prior_bodies[-1]

    out: list = []
    for stmt in body:
        if (
            isinstance(stmt, StatementExpression)
            and isinstance(stmt.expression, SuperMethodInvocation)
            and stmt.expression.member == "serialize"
        ):
            out.extend(parent_body)
            continue
        out.append(stmt)
    return out


def _body_to_ops(body: list) -> list[FieldOp]:
    """Flatten a serialize() body to leaf write/read ops.

    `if (!packet.isXxxSkipped()) { writeA(); writeB(); }` becomes two leaf
    ops, each carrying the if-condition in its signature. That way adding a
    new write inside the if block diffs as one new op (with the same
    condition) rather than rewriting the whole if-statement signature.
    """
    out: list[FieldOp] = []
    _walk_stmts(body, [], out)
    return out


def _walk_stmts(stmts: list, cond_stack: list[str], out: list[FieldOp]) -> None:
    from javalang.tree import BlockStatement, ForStatement, IfStatement, StatementExpression

    for stmt in stmts:
        if isinstance(stmt, IfStatement):
            cond = _cond_signature(stmt.condition)
            then_block = stmt.then_statement
            then_body = then_block.statements if isinstance(then_block, BlockStatement) else [then_block]
            _walk_stmts(then_body, cond_stack + [cond], out)
            if stmt.else_statement is not None:
                else_body = (
                    stmt.else_statement.statements
                    if isinstance(stmt.else_statement, BlockStatement)
                    else [stmt.else_statement]
                )
                _walk_stmts(else_body, cond_stack + [f"!({cond})"], out)
            continue
        if isinstance(stmt, ForStatement):
            body = stmt.body
            inner = body.statements if isinstance(body, BlockStatement) else [body]
            _walk_stmts(inner, cond_stack + ["@for"], out)
            continue
        if isinstance(stmt, BlockStatement):
            _walk_stmts(stmt.statements, cond_stack, out)
            continue
        if isinstance(stmt, StatementExpression):
            sig = _leaf_signature(stmt.expression)
            out.append(FieldOp(raw=stmt, signature="|".join([*cond_stack, sig])))
            continue
        # Other statement kinds (variable declarations, return, etc.) become
        # opaque leaves keyed by their type name. Coarse but stable.
        out.append(FieldOp(raw=stmt, signature="|".join([*cond_stack, type(stmt).__name__])))


def _cond_signature(expr) -> str:
    from javalang.tree import BinaryOperation, MethodInvocation, MemberReference

    if isinstance(expr, MethodInvocation):
        return f"call:{expr.member}"
    if isinstance(expr, BinaryOperation):
        return f"{_cond_signature(expr.operandl)}{expr.operator}{_cond_signature(expr.operandr)}"
    if isinstance(expr, MemberReference):
        return f"ref:{expr.qualifier or ''}.{expr.member}"
    return type(expr).__name__


def _leaf_signature(expr) -> str:
    """Two write statements compare equal iff they reach the same packet getter.

    We recurse through wrapper calls (e.g. `converter.serialize(packet.getX())`)
    until we find a `packet.getXxx`-like accessor, which is what differentiates
    fields. Without recursion, the two writeString calls inside Disconnect's
    if-block would collide on `call:serialize`.
    """
    from javalang.tree import MethodInvocation

    if not isinstance(expr, MethodInvocation):
        return type(expr).__name__
    write = f"{expr.qualifier or ''}.{expr.member}"
    targets = [_find_packet_getter(a) for a in expr.arguments or []]
    targets = [t for t in targets if t]
    if not targets:
        targets = ["?"]
    return f"{write}({','.join(targets)})"


def _find_packet_getter(expr) -> str | None:
    """Walk down nested calls until we hit packet.getXxx / packet.isXxx."""
    from javalang.tree import MethodInvocation

    if isinstance(expr, MethodInvocation):
        if (expr.qualifier or "").startswith("packet"):
            return expr.member
        for a in expr.arguments or []:
            t = _find_packet_getter(a)
            if t:
                return t
    return None


def _codec_root(cloudburst_root: Path) -> Path:
    return (
        cloudburst_root
        / "bedrock-codec"
        / "src"
        / "main"
        / "java"
        / "org"
        / "cloudburstmc"
        / "protocol"
        / "bedrock"
        / "codec"
    )
