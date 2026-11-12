"""List the packets two EndstoneMC/protocol-docs refs disagree on."""

import argparse
import json
import re
import subprocess
import sys
from itertools import zip_longest
from pathlib import Path
from typing import Any

Json = dict[str, Any]
Kinds = dict[str, dict[str, Json]]

TOKEN = re.compile(r"[A-Za-z_][\w:]*")
NOT_WIRE = {"description", "notes"}
WIRE_CONSTRAINTS = "RequestNetworkSettingsPacket"


def git(clone: Path, *args: str) -> str:
    """Run git in the clone and return its stdout."""
    return subprocess.run(["git", "-C", str(clone), *args], check=True, capture_output=True, text=True).stdout


def strip(node: Any, keep_constraints: bool) -> Any:
    """Drop the keys that never reach the wire."""
    if isinstance(node, list):
        return [strip(item, keep_constraints) for item in node]
    if isinstance(node, dict):
        return {
            key: strip(value, keep_constraints)
            for key, value in node.items()
            if key not in NOT_WIRE and (key != "constraints" or keep_constraints)
        }
    return node


def load(clone: Path, ref: str) -> Kinds:
    """Read the packets, types and enums of a ref, keyed by their declared name."""
    kinds: Kinds = {"packets": {}, "types": {}, "enums": {}}
    for path in git(clone, "ls-tree", "-r", "--name-only", ref).splitlines():
        kind, _, file = path.partition("/")
        if kind in kinds and file.endswith(".json"):
            node = json.loads(git(clone, "show", f"{ref}:{path}"))
            kinds[kind][node["name"]] = strip(node, node["name"] == WIRE_CONSTRAINTS)
    return kinds


def renames(clone: Path, old: str, new: str) -> dict[str, str]:
    """Map each type or enum name git sees renamed to its new name."""
    mapping: dict[str, str] = {}
    for line in git(clone, "diff", "--name-status", "-M", old, new).splitlines():
        status, *paths = line.split("\t")
        if status.startswith("R") and paths[0].split("/")[0] in ("types", "enums"):
            old_name = paths[0].split("/", 1)[1].removesuffix(".json").replace("__", "::")
            new_name = paths[1].split("/", 1)[1].removesuffix(".json").replace("__", "::")
            mapping[old_name] = new_name
    return mapping


class Differ:
    """Walk a packet member by member and recurse into every type it references."""

    def __init__(self, old: Kinds, new: Kinds, renamed: dict[str, str]) -> None:
        self.old = old
        self.new = new
        self.renamed = renamed
        self.done: dict[tuple[str, str, str, bool], str | None] = {}

    def spell(self, text: str) -> str:
        """Rewrite every renamed name in a type string to its new spelling."""
        return TOKEN.sub(lambda match: self.renamed.get(match.group(), match.group()), text)

    def refs(self, value: Any) -> list[str]:
        """List the names a type or enum value mentions, in order."""
        if isinstance(value, str):
            return TOKEN.findall(value)
        if isinstance(value, list):
            return [name for item in value for name in self.refs(item)]
        if isinstance(value, dict):
            return [name for item in value.values() for name in self.refs(item)]
        return []

    def respell(self, value: Any) -> Any:
        """Apply the renames to every string in a type or enum value."""
        if isinstance(value, str):
            return self.spell(value)
        if isinstance(value, list):
            return [self.respell(item) for item in value]
        if isinstance(value, dict):
            return {key: self.respell(item) for key, item in value.items()}
        return value

    def named(self, kind: str, old_name: str, by_name: bool) -> str | None:
        """Compare a type or enum by its old name against the same entity in the new ref."""
        new_name = self.renamed.get(old_name, old_name)
        key = (kind, old_name, new_name, by_name)
        if key not in self.done:
            self.done[key] = None
            old_node, new_node = self.old[kind].get(old_name), self.new[kind].get(new_name)
            if old_node and new_node and kind == "enums":
                self.done[key] = self.values(old_node["values"], new_node["values"], by_name)
            elif old_node and new_node:
                self.done[key] = self.members(old_node["fields"], new_node["fields"], new_name)
        return self.done[key]

    def values(self, old: list[Json], new: list[Json], by_name: bool) -> str | None:
        """Compare two enum value lists; names are wire only for an enum a string field carries."""
        if not by_name:
            changed = {value["value"] for value in old} ^ {value["value"] for value in new}
            return f"value {min(changed)} added or removed" if changed else None
        for old_value, new_value in zip_longest(old, new):
            if old_value != new_value:
                return f"value {_show(old_value)} -> {_show(new_value)}"
        return None

    def members(self, old: list[Json], new: list[Json], path: str) -> str | None:
        """Compare two member lists in order and describe the first difference."""
        for old_member, new_member in zip_longest(old, new):
            if old_member is None:
                return f"{path}: member '{new_member['name']}' added"
            if new_member is None:
                return f"{path}: member '{old_member['name']}' removed"
            where = f"{path}.{new_member['name']}"
            for key in sorted(old_member.keys() | new_member.keys()):
                before, after = old_member.get(key), new_member.get(key)
                if key in ("type", "enum"):
                    before = self.respell(before)
                if before != after:
                    return f"{where}: {key} {_show(old_member.get(key))} -> {_show(after)}"
            for key, kind in (("type", "types"), ("enum", "enums")):
                for name in self.refs(old_member[key]) if key in old_member else []:
                    if (name in self.old[kind]) != (self.renamed.get(name, name) in self.new[kind]):
                        return f"{where}: {kind[:-1]} {name} added or removed"
                    if (found := self.named(kind, name, old_member["type"] == "string")) is not None:
                        return f"{where} > {found}"
        return None


def _show(value: Any) -> str:
    """Render a value for the report."""
    return "none" if value is None else json.dumps(value, separators=(",", ":"))


def main() -> None:
    """Print the packets added, removed, moved and dirty between two refs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clone", type=Path, help="local EndstoneMC/protocol-docs clone")
    parser.add_argument("old", help="old branch or SHA")
    parser.add_argument("new", help="new branch or SHA")
    args = parser.parse_args()

    old, new = load(args.clone, args.old), load(args.clone, args.new)
    differ = Differ(old, new, renames(args.clone, args.old, args.new))
    lines = [f"added\t{name}" for name in sorted(new["packets"].keys() - old["packets"].keys())]
    lines += [f"removed\t{name}" for name in sorted(old["packets"].keys() - new["packets"].keys())]
    for name in sorted(old["packets"].keys() & new["packets"].keys()):
        before, after = old["packets"][name], new["packets"][name]
        if before["id"] != after["id"]:
            lines.append(f"moved\t{name}\tid {before['id']} -> {after['id']}")
        if (found := differ.members(before["fields"], after["fields"], name)) is not None:
            lines.append(f"dirty\t{name}\t{found}")
    sys.stdout.write("".join(f"{line}\n" for line in lines))


if __name__ == "__main__":
    main()
