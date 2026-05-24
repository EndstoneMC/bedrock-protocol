"""Post-process DraftFields to recognize a few common CloudburstMC patterns.

Currently handles:

- `if (!packet.isXxxSkipped()) { write a; write b; }`  ->  nested class
  `{PacketName}{Stem}` containing a and b, plus a top-level
  `xxx: ...{Stem} | None = field(type=Union)`. The two discriminator flag
  fields (bool and varint-of-bool variants) are dropped.

Everything else (instanceof checks, getMode==X discriminators, raw @for
loops, etc.) is left as inline `# CLOUDBURST_IMPORT_TODO: wrapped in ...`
comments for the reviewer to handle by hand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .mappings import DraftField, _to_snake


@dataclass
class NestedClass:
    name: str
    fields: list[DraftField]


_SKIPPED_RE = re.compile(r"^call:is([A-Z][A-Za-z0-9]*)Skipped$")


def group_optional_unions(
    fields: list[DraftField],
    packet_name: str,
) -> tuple[list[DraftField], list[NestedClass]]:
    """Walk the field list, fold `isXxxSkipped`-wrapped runs into a Union."""
    classes: list[NestedClass] = []
    out: list[DraftField] = []
    # Names that should drop from the output because they're now discriminators
    # encoded by the Union (`message_skipped`, etc.).
    dropped_names: set[str] = set()

    i = 0
    while i < len(fields):
        f = fields[i]
        if not f.cond_chain:
            out.append(f)
            i += 1
            continue

        leaf_cond = f.cond_chain[-1]
        m = _SKIPPED_RE.match(leaf_cond)
        if m is None:
            out.append(f)
            i += 1
            continue

        stem = m.group(1)  # e.g. "Message"
        run_end = i
        while (
            run_end < len(fields)
            and fields[run_end].cond_chain == f.cond_chain
        ):
            run_end += 1

        nested_name = f"{packet_name[:-len('Packet')] if packet_name.endswith('Packet') else packet_name}Packet{_pluralize(stem)}"
        outer_field_name = _to_snake(_pluralize(stem))

        inner_fields = [_strip_cond(g) for g in fields[i:run_end]]
        classes.append(NestedClass(name=nested_name, fields=inner_fields))

        out.append(
            DraftField(
                name=outer_field_name,
                dsl_type=f"{nested_name} | None",
                extras={"type": "Union"},
                todo=None,
                cond_chain=[],
            )
        )
        dropped_names.add(_to_snake(stem) + "_skipped")
        i = run_end

    # Drop any leftover discriminator fields (they may appear both before and
    # after the if-block in different version chains).
    filtered = [f for f in out if f.name not in dropped_names]
    return filtered, classes


def _pluralize(stem: str) -> str:
    if stem.endswith("s"):
        return stem
    if stem.endswith("y") and len(stem) > 1 and stem[-2] not in "aeiou":
        return stem[:-1] + "ies"
    return stem + "s"


def _strip_cond(f: DraftField) -> DraftField:
    return DraftField(
        name=f.name,
        dsl_type=f.dsl_type,
        extras=dict(f.extras),
        todo=f.todo,
        cond_chain=[],
    )
