"""CLI entry point.

Examples:
  python -m cloudburst_import --cloudburst d:/tmp/cloudburstmc-protocol \\
      --packet DisconnectPacket
  python -m cloudburst_import --cloudburst d:/tmp/cloudburstmc-protocol \\
      --all --out protocol/_drafts/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .emit import PacketDraft, render
from .enums import collect_enum_drafts
from .grouping import group_optional_unions
from .mappings import translate_op
from .parser import parse_packet_class
from .version_chain import (
    PacketInfo,
    build_packet_registry,
    derive_field_history,
    find_serializer_chain,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cloudburst_import")
    p.add_argument(
        "--cloudburst",
        required=True,
        type=Path,
        help="path to a CloudburstMC/Protocol git checkout",
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--packet", help="single packet class name, e.g. DisconnectPacket")
    group.add_argument("--all", action="store_true", help="dump every registered packet to --out")
    p.add_argument("--out", type=Path, default=None, help="output directory (required with --all)")

    args = p.parse_args(argv)

    if not args.cloudburst.exists():
        print(f"error: --cloudburst path does not exist: {args.cloudburst}", file=sys.stderr)
        return 1

    registry = build_packet_registry(args.cloudburst)

    if args.packet:
        info = registry.get(args.packet)
        if info is None:
            print(f"error: packet {args.packet!r} not found in registry", file=sys.stderr)
            print(f"hint: known packets start with: {', '.join(sorted(registry)[:5])} ...", file=sys.stderr)
            return 1
        text = _generate(args.cloudburst, info)
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            target = args.out / (_module_name_for(info.name) + ".py")
            target.write_text(text, encoding="utf-8")
            print(f"wrote {target}")
        else:
            print(text)
        return 0

    if not args.out:
        print("error: --all requires --out", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    ok = 0
    bad = 0
    for name in sorted(registry):
        info = registry[name]
        try:
            text = _generate(args.cloudburst, info)
        except Exception as exc:  # noqa: BLE001 - draft tool, surface and continue
            bad += 1
            print(f"FAIL {name}: {exc}", file=sys.stderr)
            continue
        target = args.out / (_module_name_for(name) + ".py")
        target.write_text(text, encoding="utf-8")
        ok += 1
    print(f"wrote {ok} drafts, {bad} failed, into {args.out}")
    return 0 if bad == 0 else 2


def _generate(cloudburst: Path, info: PacketInfo) -> str:
    chain = find_serializer_chain(cloudburst, info.name)
    java_field_types = _load_java_field_types(cloudburst, info.name)
    if not chain:
        return render(PacketDraft(info=info, chain=[], fields=[], enums=[], nested=[]))
    history = derive_field_history(chain)
    fields = [translate_op(op, java_field_types) for op in history]
    fields = [
        f
        for f in fields
        if not (
            f.dsl_type == "bytes"
            and (f.todo or "").startswith("CLOUDBURST_IMPORT_TODO: non-call statement")
        )
    ]
    fields, nested = group_optional_unions(fields, info.name)
    refs = _collect_enum_refs(fields) + [
        tok for nc in nested for f in nc.fields for tok in _extract_type_tokens(f.dsl_type)
    ]
    enums = collect_enum_drafts(cloudburst, refs)
    return render(
        PacketDraft(info=info, chain=chain, fields=fields, enums=enums, nested=nested)
    )


def _collect_enum_refs(fields) -> list[str]:
    """DSL types that look like an enum/struct name we should try to resolve."""
    refs: list[str] = []
    seen: set[str] = set()
    skip = {"str", "bool", "bytes", "list", "dict", "tuple", "uuid.UUID"}
    for f in fields:
        for token in _extract_type_tokens(f.dsl_type):
            if token in skip or token in seen:
                continue
            if not token[:1].isupper():
                continue
            seen.add(token)
            refs.append(token)
    return refs


def _extract_type_tokens(dsl_type: str) -> list[str]:
    import re as _re

    return _re.findall(r"[A-Za-z_][A-Za-z_0-9.]*", dsl_type)


def _load_java_field_types(cloudburst: Path, packet_class: str) -> dict[str, str]:
    """Snake-case map of packet-class field names to their Java types."""
    candidate = (
        cloudburst
        / "bedrock-codec/src/main/java/org/cloudburstmc/protocol/bedrock/packet"
        / f"{packet_class}.java"
    )
    if not candidate.exists():
        return {}
    try:
        pkt = parse_packet_class(candidate)
    except Exception:  # noqa: BLE001 - draft tool; missing types are fine
        return {}
    import re as _re

    types: dict[str, str] = {}
    for f in pkt.fields:
        snake = _re.sub(r"(?<!^)(?=[A-Z])", "_", f.name).lower()
        types[snake] = f.java_type
    return types


def _module_name_for(packet_class: str) -> str:
    """ServerStoreInfoPacket -> server_store_info."""
    base = packet_class
    if base.endswith("Packet"):
        base = base[: -len("Packet")]
    import re
    return re.sub(r"(?<!^)(?=[A-Z])", "_", base).lower()


if __name__ == "__main__":
    raise SystemExit(main())
