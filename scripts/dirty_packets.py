"""List the packets two EndstoneMC/protocol-docs refs disagree on."""

import argparse
import json
import subprocess
from itertools import zip_longest
from pathlib import Path
from typing import Any

Json = dict[str, Any]
Kinds = dict[str, dict[str, Json]]

WIRE_CONSTRAINTS = "RequestNetworkSettingsPacket"


def git(clone: Path, *args: str) -> str:
    """Run git in the clone and return its stdout."""
    return subprocess.run(["git", "-C", str(clone), *args], check=True, stdout=subprocess.PIPE, text=True).stdout


def load(clone: Path, ref: str) -> Kinds:
    """Read the packets, types and enums of a ref, keyed by their declared name."""
    kinds: Kinds = {"packets": {}, "types": {}, "enums": {}}
    for path in git(clone, "ls-tree", "-r", "--name-only", ref).splitlines():
        kind, _, file = path.partition("/")
        if kind in kinds and file.endswith(".json"):
            node = json.loads(git(clone, "show", f"{ref}:{path}"))
            for member in node.get("fields", []) if node["name"] != WIRE_CONSTRAINTS else []:
                member.pop("constraints", None)
            kinds[kind][node["name"]] = node
    return kinds


class Differ:
    """Walk a packet member by member and recurse into every type it references."""

    def __init__(self, old: Kinds, new: Kinds, renamed: dict[str, str]) -> None:
        self.old = old
        self.new = new
        self.renamed = renamed
        self.done: dict[tuple[str, str, str, bool], str | None] = {}

    def refs(self, value: Any) -> list[tuple[str, str, bool]]:
        """List the types and enums a type or member value references, in order."""
        if isinstance(value, str):
            return [("types", value, False)]
        if isinstance(value, list):
            return [ref for item in value for ref in self.refs(item)]
        if isinstance(value, dict):
            refs = [("enums", value["enum"], value.get("type") == "string")] if "enum" in value else []
            return refs + [ref for key, item in value.items() if key not in ("name", "enum") for ref in self.refs(item)]
        return []

    def respell(self, value: Any) -> Any:
        """Apply the renames to every string in a type or enum value."""
        if isinstance(value, str):
            return self.renamed.get(value, value)
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
            if old_node and new_node and kind == "enums" and by_name:
                self.done[key] = next(
                    (
                        f"value {show(a)} -> {show(b)}"
                        for a, b in zip_longest(old_node["values"], new_node["values"])
                        if a != b
                    ),
                    None,
                )
            elif old_node and new_node and kind == "enums":
                changed = {v["value"] for v in old_node["values"]} ^ {v["value"] for v in new_node["values"]}
                self.done[key] = f"value {min(changed)} added or removed" if changed else None
            elif old_node and new_node:
                self.done[key] = self.members(old_node["fields"], new_node["fields"], new_name)
        return self.done[key]

    def members(self, old: list[Json], new: list[Json], path: str) -> str | None:
        """Compare two member lists in order and describe the first difference."""
        for old_member, new_member in zip_longest(old, new):
            if old_member is None:
                return f"{path}: member '{new_member.get('name')}' added"
            if new_member is None:
                return f"{path}: member '{old_member.get('name')}' removed"
            where = f"{path}.{new_member.get('name')}"
            for key in sorted(old_member.keys() | new_member.keys()):
                before, after = old_member.get(key), new_member.get(key)
                if key in ("type", "enum"):
                    before = self.respell(before)
                if before != after:
                    return f"{where}: {key} {show(old_member.get(key))} -> {show(after)}"
            for kind, name, by_name in self.refs(old_member):
                if (name in self.old[kind]) != (self.renamed.get(name, name) in self.new[kind]):
                    return f"{where}: {kind[:-1]} {name} added or removed"
                if (found := self.named(kind, name, by_name)) is not None:
                    return f"{where} > {found}"
        return None


def show(value: Any) -> str:
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
    renamed: dict[str, str] = {}
    for line in git(args.clone, "diff", "--name-status", "-M", args.old, args.new).splitlines():
        status, *paths = line.split("\t")
        if status.startswith("R") and paths[0].split("/")[0] in ("types", "enums"):
            old_name = json.loads(git(args.clone, "show", f"{args.old}:{paths[0]}"))["name"]
            renamed[old_name] = json.loads(git(args.clone, "show", f"{args.new}:{paths[1]}"))["name"]
    differ = Differ(old, new, renamed)
    for name in sorted(new["packets"].keys() - old["packets"].keys()):
        print(f"added\t{name}")
    for name in sorted(old["packets"].keys() - new["packets"].keys()):
        print(f"removed\t{name}")
    for name in sorted(old["packets"].keys() & new["packets"].keys()):
        before, after = old["packets"][name], new["packets"][name]
        if before["id"] != after["id"]:
            print(f"moved\t{name}\tid {before['id']} -> {after['id']}")
        if (found := differ.members(before["fields"], after["fields"], name)) is not None:
            print(f"dirty\t{name}\t{found}")


if __name__ == "__main__":
    main()
