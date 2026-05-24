"""Locate and parse CloudburstMC enum types referenced from a packet draft.

CloudburstMC keeps enum types under `bedrock-codec/.../bedrock/data/**/*.java`.
We index that tree once per run, then for each enum referenced by a draft we
parse the members (ordinal or explicit-value) and emit an `@type` IntEnum
block. No `since=NNN` per member — that requires git-log history which is out
of scope for the draft. The reviewer fills that in by cross-checking against
gophertunnel and bedrock-protocol-docs (CLAUDE.md rule 7).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import javalang
from javalang.tree import (
    ClassDeclaration,
    EnumConstantDeclaration,
    EnumDeclaration,
    Literal,
)


@dataclass
class EnumMember:
    name: str
    value: int | None  # None when ordinal-numbered (no explicit value)


@dataclass
class EnumDraft:
    name: str
    members: list[EnumMember]
    explicit_values: bool  # True if the Java enum used `MEMBER(N)` syntax


@cache
def _data_index(cloudburst_root: Path) -> dict[str, Path]:
    """Map enum/class simple name to its `.java` path, indexed once per run."""
    base = (
        cloudburst_root
        / "bedrock-codec/src/main/java/org/cloudburstmc/protocol/bedrock/data"
    )
    out: dict[str, Path] = {}
    if not base.exists():
        return out
    for path in base.rglob("*.java"):
        name = path.stem
        # Keep the first occurrence — duplicates across sub-packages are rare
        # and the reviewer will catch the mismatch.
        out.setdefault(name, path)
    return out


def collect_enum_drafts(cloudburst_root: Path, names: list[str]) -> list[EnumDraft]:
    """Return enum drafts for the given Java type names, in input order.

    Names that don't resolve to a Java enum (e.g. struct classes, missing
    files) are silently skipped — the draft still references them and the
    reviewer's TODO comment will catch it.
    """
    index = _data_index(cloudburst_root)
    drafts: list[EnumDraft] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        path = index.get(name)
        if not path:
            continue
        draft = _parse_enum(path)
        if draft is not None:
            drafts.append(draft)
    return drafts


def _parse_enum(path: Path) -> EnumDraft | None:
    src = path.read_text(encoding="utf-8")
    try:
        tree = javalang.parse.parse(src)
    except Exception:  # noqa: BLE001 - draft tool, skip unparseable files
        return None
    decl: EnumDeclaration | ClassDeclaration | None = None
    for type_decl in tree.types:
        if isinstance(type_decl, EnumDeclaration):
            decl = type_decl
            break
    if decl is None:
        return None

    members: list[EnumMember] = []
    explicit = False
    for body_member in decl.body.constants if hasattr(decl.body, "constants") else []:
        if not isinstance(body_member, EnumConstantDeclaration):
            continue
        value: int | None = None
        if body_member.arguments:
            arg = body_member.arguments[0]
            if isinstance(arg, Literal):
                try:
                    raw = int(arg.value, 0)
                    if "-" in (arg.prefix_operators or []):
                        raw = -raw
                    value = raw
                except (TypeError, ValueError):
                    value = None
        if value is not None:
            explicit = True
        members.append(EnumMember(name=body_member.name, value=value))

    return EnumDraft(name=path.stem, members=members, explicit_values=explicit)
