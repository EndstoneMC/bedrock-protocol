"""Compares each golden case with what BDS wrote and printed for it, naming every rule the match needs."""

import collections
import json
import os
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bedrock_protocol_compiler.builder import build
from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    Array,
    BuiltinRef,
    EnumName,
    EnumRef,
    List,
    Literal,
    Map,
    MemberRef,
    Optional,
    Primitive,
    StructRef,
    Type,
    Variant,
)
from bedrock_protocol_compiler.schema import EnumShape, Schema, StructShape


@dataclass
class Ours:
    """A part of the case's value, with the type our schema declares for it."""

    value: Any
    type: Type


@dataclass
class Bds:
    """A part of the JSON BDS printed, with the field the dump declares for it."""

    value: Any
    field: dict[str, Any]

    @property
    def fields(self) -> list[dict[str, Any]] | None:
        """The fields of the struct this field's type names, if it names one."""
        return bds_structs.get(self.field["type"]) if isinstance(self.field["type"], str) else None


def bds_prints_the_wire_type(ours: Ours, bds: Bds) -> tuple[Ours, Bds] | None:
    match ours.type:
        case Primitive(wire=str(wire)) | AliasRef(wire=str(wire)) if wire == bds.field["type"]:
            bits = int("".join(filter(str.isdigit, wire)))
            return Ours(ours.value % 2**bits, Primitive(wire)), bds
    return None


def bds_prints_a_bool_enum_as_a_bool(ours: Ours, bds: Bds) -> tuple[Ours, Bds] | None:
    if isinstance(ours.type, EnumRef) and bds.field["type"] == "bool":
        return Ours(bool(enum_shapes[ours.type.enum].numbers[ours.value]), ours.type), bds
    return None


def bds_prints_an_enum_as_its_number(ours: Ours, bds: Bds) -> tuple[Ours, Bds] | None:
    if isinstance(ours.type, EnumRef) and isinstance(ours.value, str) and type(bds.value) is int:
        return Ours(enum_shapes[ours.type.enum].numbers[ours.value], ours.type), bds
    return None


def bds_prints_an_enum_as_its_wire_name(ours: Ours, bds: Bds) -> tuple[Ours, Bds] | None:
    if isinstance(ours.type, EnumName):
        members = enum_shapes[ours.type.enum].members
        return Ours(next(each.wire_name for each in members if each.name == ours.value), ours.type), bds
    return None


def bds_prints_bytes_as_text(ours: Ours, bds: Bds) -> tuple[Ours, Bds] | None:
    if ours.type == Primitive("bytes") and isinstance(bds.value, str):
        return ours, Bds(bds.value.encode("utf-8", "surrogateescape").hex(), bds.field)
    return None


def bds_prints_bytes_as_numbers(ours: Ours, bds: Bds) -> tuple[Ours, Bds] | None:
    if ours.type == Primitive("bytes") and bds.field["type"] == "uint8" and isinstance(bds.value, list):
        return ours, Bds(bytes(bds.value).hex(), bds.field)
    return None


def bds_prints_a_literal_field(ours: Ours, bds: Bds) -> tuple[Ours, Bds] | None:
    match ours.type:
        case Literal(value=MemberRef(enum=enum, name=name)) if "name" in bds.field:
            return Ours(enum_shapes[enum].numbers[name], ours.type), bds
        case Literal(value=value) if "name" in bds.field:
            return Ours(value, ours.type), bds
    return None


BDS_WRAPPERS = {"ActorRuntimeID", "ActorUniqueID", "DimensionType", "PlayerInputTick", "mce::Color"}


def bds_wraps_a_value_in_a_one_member_type(ours: Ours, bds: Bds) -> tuple[Ours, Bds] | None:
    if bds.fields is not None and bds.field["type"] in BDS_WRAPPERS and isinstance(bds.value, dict):
        [member] = bds.fields
        return ours, Bds(bds.value[member["name"]], member)
    return None


def bds_prints_a_one_member_struct_as_its_member(ours: Ours, bds: Bds) -> tuple[Ours, Bds] | None:
    if isinstance(ours.type, StructRef) and len(struct_shapes[ours.type.struct].fields) == 1:
        [member] = struct_shapes[ours.type.struct].fields
        return Ours(ours.value[member.name], member.type), bds
    return None


type Rule = Callable[[Ours, Bds], tuple[Ours, Bds] | None]

ACCEPTED = {
    "bds_prints_the_wire_type",
    "bds_prints_an_enum_as_its_number",
    "bds_wraps_a_value_in_a_one_member_type",
}

RULES: list[Rule] = [
    bds_prints_the_wire_type,
    bds_prints_a_bool_enum_as_a_bool,
    bds_prints_an_enum_as_its_number,
    bds_prints_an_enum_as_its_wire_name,
    bds_prints_bytes_as_text,
    bds_prints_bytes_as_numbers,
    bds_prints_a_literal_field,
    bds_wraps_a_value_in_a_one_member_type,
    bds_prints_a_one_member_struct_as_its_member,
]


def variant_tag(arm: Type) -> str:
    """The key `to_json` gives a variant arm of this type."""
    match arm:
        case StructRef(struct=family) | EnumRef(enum=family):
            return family.name
        case Primitive(name="bool" | "str" | "bytes" as name):
            return name
        case Primitive(name="float" | "double"):
            return "float"
        case Primitive() | AliasRef():
            return "int"
        case BuiltinRef():
            return "UUID"
    return "list"


def field_of(bds_type: Any) -> dict[str, Any]:
    """The field for a type the dump nests, which a fixed array or an enum-bound key already is."""
    return bds_type if isinstance(bds_type, dict) and "type" in bds_type else {"type": bds_type}


def same(ours: Ours, bds: Bds) -> bool:
    """Whether the two are equal leaves, an NBT tag being one leaf compared as exact JSON."""
    if isinstance(ours.type, BuiltinRef) and ours.type.builtin.stem == "nbt":
        return json.dumps(ours.value) == json.dumps(bds.value)
    if isinstance(ours.value, dict | list):
        return ours.value == bds.value and not ours.value
    kinds = {type(ours.value), type(bds.value)}
    return ours.value == bds.value and (len(kinds) == 1 or kinds == {int, float})


def children(ours: Ours, bds: Bds) -> list[tuple[str, Ours, Bds]] | None:
    """Pairs each part of our value with the part of BDS's value that both models put in its place."""
    match ours.type:
        case Optional(element=element) if ours.value is not None:
            return [("", Ours(ours.value, element), bds)]
        case StructRef(struct=declared) if isinstance(bds.value, dict) and bds.fields is not None:
            fields = [each for each in struct_shapes[declared].fields for _ in range(each.copies)]
            if len(fields) != len(bds.fields) or bds.value.keys() - {each.get("name") for each in bds.fields}:
                return None
            return [
                (
                    each.name,
                    Ours(ours.value.get(each.name), each.type),
                    Bds(bds.value.get(bds_each.get("name")), bds_each),
                )
                for each, bds_each in zip(fields, bds.fields, strict=True)
            ]
        case List(element=element) | Array(element=element) if "repeat" in bds.field and isinstance(bds.value, list):
            if len(ours.value) != len(bds.value):
                return None
            item_field = field_of(bds.field["type"])
            return [
                (str(index), Ours(ours_item, element), Bds(bds_item, item_field))
                for index, (ours_item, bds_item) in enumerate(zip(ours.value, bds.value, strict=True))
            ]
        case Variant(cases=arms) if isinstance(bds.value, dict) and bds.value.keys() == ours.value.keys():
            [(tag, value)] = ours.value.items()
            index, arm = next((i, arm) for i, arm in enumerate(arms) if arm and variant_tag(arm) == tag)
            return [(tag, Ours(value, arm), Bds(bds.value[tag], field_of(bds.field["type"]["cases"][index])))]
        case Map(key=key_type, value=item_type) if isinstance(bds.value, dict) and len(ours.value) == len(bds.value):
            key_field, item_field = field_of(bds.field["type"]["key"]), field_of(bds.field["type"]["value"])
            items = zip(ours.value.items(), bds.value.items(), strict=True)
            pairs = []
            for index, ((ours_key, ours_item), (bds_key, bds_item)) in enumerate(items):
                pairs.append((f"{index}/key", Ours(ours_key, key_type), Bds(bds_key, key_field)))
                pairs.append((f"{index}/value", Ours(ours_item, item_type), Bds(bds_item, item_field)))
            return pairs
    return None


def walk(ours: Ours, bds: Bds, path: str, rules: list[Rule]) -> Iterator[str]:
    """Yields each rule the match needs and each difference that no rule explains."""
    if same(ours, bds):
        return
    if (pairs := children(ours, bds)) is not None:
        for key, ours_part, bds_part in pairs:
            yield from walk(ours_part, bds_part, f"{path}/{key}", RULES)
        return
    for rule in rules:
        if (pair := rule(ours, bds)) is not None:
            yield rule.__name__
            yield from walk(*pair, path, [other for other in rules if other is not rule])
            return
    yield f"{path or '/'}: {ours.value!r} against {bds.value!r}"


folder, evidence = map(Path, sys.argv[1:])
protocol = int(folder.name.removeprefix("v"))
schema = Schema(build(Path("protocol")))
live = [shape for (_, version), shape in schema.live.items() if version == protocol]
struct_shapes = {shape.family: shape for shape in live if isinstance(shape, StructShape)}
enum_shapes = {shape.family: shape for shape in live if isinstance(shape, EnumShape)}
packets = {family.packet_id: family for family in struct_shapes if family.packet_id is not None}
bds_types = [json.loads(p.read_text()) for p in (evidence / "dump/protocol/types").glob("*.json")]
bds_packets = [json.loads(p.read_text()) for p in (evidence / "dump/protocol/packets").glob("*.json")]
bds_structs: dict[str, list[dict[str, Any]]] = {each["name"]: each["fields"] for each in bds_types + bds_packets}
bds_packet_names = {each["id"]: each["name"] for each in bds_packets}

cases = {(p.stem, i): case for p in folder.glob("*.json") for i, case in enumerate(json.loads(p.read_text()))}
verdicts: collections.Counter[str] = collections.Counter()
needs: collections.Counter[str] = collections.Counter()
frozen = 0
for result in json.loads((evidence / "results.json").read_text()):
    case = cases[result["stem"], result["index"]]
    name = f"{result['stem']}[{case['id']}]"
    needed: list[str] = []
    if "crash" in result:
        verdict, detail = "crashed", result["crash"]
    elif not result["read_ok"]:
        error = result["error"]
        verdict, detail = "refused", f"at {result['consumed']}, {error['category']}:{error['code']} {error['message']}"
    elif result["bds_bytes"] != case["bytes"]:
        verdict, detail = "rewritten", f"at {len(os.path.commonprefix([result['bds_bytes'], case['bytes']])) // 2}"
    elif "bds_json_error" in result:
        verdict, detail = "unprinted", result["bds_json_error"]
    else:
        packet = int(result["stem"][:3])
        ours = Ours(case["value"], StructRef(packets[packet]))
        bds = Bds(result["bds_json"], {"type": bds_packet_names[packet]})
        findings = list(walk(ours, bds, "", RULES))
        needed = [rule.__name__ for rule in RULES if rule.__name__ in findings]
        differences = [each for each in findings if each not in needed]
        verdict, detail = ("json_differs", f"at {differences[0]}") if differences else ("agrees", "")
    freezes = verdict == "agrees" and set(needed) <= ACCEPTED
    verdicts[verdict] += 1
    needs.update(needed)
    frozen += freezes
    line = [name, verdict, detail, *needed, "freezes" if freezes else ""]
    sys.stdout.write(" ".join(filter(None, line)) + "\n")
sys.stdout.write(", ".join(f"{count} {verdict}" for verdict, count in verdicts.most_common()) + f"; {frozen} freeze\n")
for rule in RULES:
    sys.stdout.write(f"{needs[rule.__name__]:4} {rule.__name__}{' (accepted)' if rule.__name__ in ACCEPTED else ''}\n")
