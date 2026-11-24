from pathlib import Path

import pytest

from bedrock_protocol_compiler.builder import build
from bedrock_protocol_compiler.descriptor import (
    Binary,
    CompilerError,
    EnumName,
    EnumRef,
    Int,
    List,
    MemberRef,
    Primitive,
    Range,
    StructRef,
)
from bedrock_protocol_compiler.schema import Numbering, Schema, SerializationMode, Slot, roots_reached

ROOT = Path(__file__).parents[2]

HEADER = """
from enum import IntEnum, auto
from typing import Literal
from protocol import array, bitset, field, int8, int32, packet, sentinel, type, uint8, uint16, value, varint32
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"
"""

APPENDED_INIT = """
from bedrock_protocol_compiler.dsl import (
    array, bitset, field, int8, int32, packet, sentinel, type, uint8, uint16, value, varint32
)

versions = {1: "1.1.0", 2: "1.2.0", 3: "1.3.0", 4: "1.4.0", 5: "1.5.0", 6: "1.6.x"}
"""

BOSS = """
from enum import IntEnum
from protocol import field, packet, int64, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

type ActorUniqueID = int64


class BossEventUpdateType(IntEnum, uint8):
    ADD = 0
    PLAYER_ADDED = 1
    UPDATE_NAME = 5


@packet(id=74, until=1001)
class BossEventPacket:
    boss_id: ActorUniqueID
    event_type: BossEventUpdateType
    player_id: ActorUniqueID = field(when=lambda p: p.event_type == BossEventUpdateType.PLAYER_ADDED)

    with field(when=lambda p: p.event_type in {BossEventUpdateType.ADD, BossEventUpdateType.UPDATE_NAME}):
        name: str
        filtered_name: str = field(since=776)

    health_percent: float


@packet(id=74, since=1001)
class BossEventPacket:
    boss_id: ActorUniqueID
    player_id: ActorUniqueID = field(until=2193)
    event_type: BossEventUpdateType
    name: str
    filtered_name: str
    health_percent: float
"""

SOUND = """
from protocol import field, packet, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@packet(id=348, since=2168)
class ClientboundUpdateSoundDataPacket:
    event: uint8 = field(duplicate=7, until=2225)
    event: uint8 = field(since=2225)
"""

MODELLED_INIT = """
from bedrock_protocol_compiler.dsl import field, int64, packet, type, uint8, uint16, value

versions = {
    729: "1.21.30-1.21.31",
    748: "1.21.40-1.21.44",
    766: "1.21.50-1.21.51",
    776: "1.21.60-1.21.62",
    786: "1.21.70-1.21.73",
    800: "1.21.80-1.21.84",
    818: "1.21.90-1.21.92",
    819: "1.21.93-1.21.95",
    827: "1.21.100-1.21.102",
    844: "1.21.111-1.21.114",
    859: "1.21.120-1.21.123",
    860: "1.21.124",
    898: "1.21.130-1.21.132",
    924: "1.26.0-1.26.3",
    944: "1.26.10-1.26.14",
    975: "1.26.20-1.26.23",
    1001: "1.26.30-1.26.36",
    2168: "1.26.40-1.26.44",
    2169: "1.26.45",
    2193: "1.26.50-1.26.52",
    2225: "1.26.6x",
}
"""


def names(shape):
    return [each.name for each in shape.fields]


def test_boss_changes_shape_at_776_1001_and_2193(build_package):
    schema = Schema(build_package({"boss": BOSS}, MODELLED_INIT))
    packet = schema.order[-1]

    shapes = schema.shapes(packet)

    assert [shape.ranges for shape in shapes] == [
        [Range(None, 776)],
        [Range(776, 1001)],
        [Range(1001, 2193)],
        [Range(2193, None)],
    ]
    assert names(schema.shape_at(packet, 776)) == [
        "boss_id",
        "event_type",
        "player_id",
        "name",
        "filtered_name",
        "health_percent",
    ]
    assert names(schema.shape_at(packet, 1001)) == [
        "boss_id",
        "player_id",
        "event_type",
        "name",
        "filtered_name",
        "health_percent",
    ]
    assert names(schema.shape_at(packet, 2193)) == ["boss_id", "event_type", "name", "filtered_name", "health_percent"]


def test_a_shape_that_returns_is_one_shape_with_two_ranges(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    x: uint8\n\n"
        + "@type(since=3, until=4)\nclass A:\n    y: uint8\n\n"
        + "@type(since=4)\nclass A:\n    x: uint8\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    first, second = schema.shapes(family)

    assert first.ranges == [Range(None, 3), Range(4, None)]
    assert second.ranges == [Range(3, 4)]
    assert schema.shape_at(family, 5) is first


def test_a_family_with_one_shape_over_every_version_is_unversioned(build_package):
    schema = Schema(build_package({"a": HEADER + "class A:\n    x: uint8\n"}))
    (family,) = schema.order

    (shape,) = schema.shapes(family)

    assert (shape.ranges, shape.versioned) == ([Range(None, None)], False)


def test_a_family_that_stops_early_is_versioned(build_package):
    schema = Schema(build_package({"a": HEADER + "@type(until=4)\nclass A:\n    x: uint8\n"}))
    (family,) = schema.order

    (shape,) = schema.shapes(family)

    assert (shape.ranges, shape.versioned) == ([Range(None, 4)], True)


def test_a_reached_family_that_changes_changes_the_owner(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass B:\n    x: uint8\n\n@type(since=3)\nclass B:\n    y: uint8\n\n"
        + "class A:\n    b: B\n"
    )
    schema = Schema(build_package({"a": source}))
    _, a = schema.order

    assert [shape.ranges for shape in schema.shapes(a)] == [[Range(None, 3)], [Range(3, None)]]


def test_a_nested_shape_is_owned_by_the_first_owner_shape_that_holds_it(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    class B:\n        x: uint8\n    b: B\n\n"
        + "@type(since=3)\nclass A:\n    class B:\n        x: uint8\n    b: B\n    y: uint8\n"
    )
    schema = Schema(build_package({"a": source}))
    nested, owner = schema.order

    (inner,) = schema.shapes(nested)
    early, late = schema.shapes(owner)

    assert inner.ranges == [Range(None, None)]
    assert early.nested == late.nested == (inner,)
    assert inner.owner is early


def test_a_new_nested_shape_opens_a_new_owner_shape(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    class B:\n        x: uint8\n    b: B\n\n"
        + "@type(since=3)\nclass A:\n    class B:\n        y: uint8\n    b: B\n"
    )
    schema = Schema(build_package({"a": source}))
    nested, owner = schema.order

    old, new = schema.shapes(nested)
    early, late = schema.shapes(owner)

    assert (old.owner, new.owner) == (early, late)


def test_a_deeper_nested_shape_is_owned_by_its_mid_shape(build_package):
    source = HEADER + "class A:\n    class B:\n        class C:\n            x: uint8\n        c: C\n    b: B\n"
    schema = Schema(build_package({"a": source}))
    deep, mid, top = schema.order

    assert schema.shapes(deep)[0].owner is schema.shapes(mid)[0]
    assert schema.shapes(mid)[0].owner is schema.shapes(top)[0]


def test_a_nested_family_absent_at_a_version_is_left_out_of_its_owner(build_package):
    source = HEADER + "class A:\n    @type(since=3)\n    class B:\n        x: uint8\n    y: uint8\n"
    schema = Schema(build_package({"a": source}))
    nested, owner = schema.order

    before, after = schema.shapes(owner)

    assert (before.nested, after.nested) == ((), (schema.shapes(nested)[0],))


def test_a_struct_that_reaches_a_pre_cereal_family_does_not_change_with_the_cereal_one(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass B:\n    x: uint8\n\n@type(since=3)\nclass B:\n    x: uint16\n\n"
        + "@type(cereal=False)\nclass B:\n    x: uint8\n\n"
        + "@packet(id=1)\nclass A:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, pre_cereal, a = schema.order

    assert len(schema.shapes(cereal)) == 2
    assert len(schema.shapes(pre_cereal)) == 1
    assert len(schema.shapes(a)) == 1


def test_a_family_comes_after_the_families_it_reaches(build_package):
    source = HEADER + "class A:\n    b: B\n\nclass B:\n    c: C\n\nclass C:\n    x: uint8\n"
    schema = Schema(build_package({"a": source}))

    assert [family.name for family in schema.order] == ["C", "B", "A"]


def test_the_latest_version_is_the_last_one(build_package):
    schema = Schema(build_package({"a": HEADER + "class A:\n    x: uint8\n"}))

    assert (schema.versions, schema.latest) == ((1, 5), 5)


def test_enum_values_are_evaluated_over_the_members_present(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 4\n    B = value(5, since=3)\n    C = auto()\n    D = C\n    F = C - 1\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    early, late = schema.shapes(family)

    assert [(member.name, member.value) for member in early.members] == [
        ("A", Int(4)),
        ("C", Int(5)),
        ("D", MemberRef(family, "C")),
        ("F", Binary("-", MemberRef(family, "C"), Int(1))),
    ]
    assert late.numbers == {"A": 4, "B": 5, "C": 6, "D": 6, "F": 5}


def test_auto_inside_an_enum_block_counts_the_members_present(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n    with value(since=3):\n        B = 2, 'Bee'\n        C = auto()\n"
        + "    D = auto()\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert [shape.numbers for shape in schema.shapes(family)] == [{"A": 1, "D": 2}, {"A": 1, "B": 2, "C": 3, "D": 4}]


def test_a_sentinel_takes_the_number_auto_would_give_and_is_no_member(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = sentinel()\n    C = auto()\n    D = 7\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (shape,) = schema.shapes(family)

    assert ([member.name for member in shape.members], shape.numbers) == (
        ["A", "C", "D"],
        {"A": 1, "B": 2, "C": 3, "D": 7},
    )


def test_a_deprecated_member_stays_a_member_of_its_shape(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = value(2, deprecated=True)\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (shape,) = schema.shapes(family)

    assert [(member.name, member.deprecated) for member in shape.members] == [("A", False), ("B", True)]


def test_a_gated_sentinel_is_a_member_outside_its_gate(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n    with value(until=3):\n        B = sentinel()\n"
        + "    B = value(since=3)\n    C = auto()\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert [([member.name for member in shape.members], shape.numbers) for shape in schema.shapes(family)] == [
        (["A", "C"], {"A": 1, "B": 2, "C": 3}),
        (["A", "B", "C"], {"A": 1, "B": 2, "C": 3}),
    ]


def test_an_enum_whose_sentinel_alone_moves_is_a_new_shape(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n    with value(until=3):\n        B = sentinel()\n"
        + "    COUNT = sentinel()\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert [shape.numbers for shape in schema.shapes(family)] == [{"A": 1, "B": 2, "COUNT": 3}, {"A": 1, "COUNT": 2}]


def test_an_enum_member_renamed_at_the_same_value_is_a_new_shape(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = value(2, since=3)\n    C = value(2, until=3)\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    shapes = schema.shapes(family)

    assert [shape.ranges for shape in shapes] == [[Range(None, 3)], [Range(3, None)]]


def test_an_enum_whose_declarations_name_two_underlying_types_is_rejected(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass E(IntEnum, uint8):\n    A = 1\n\n"
        + "@type(since=3)\nclass E(IntEnum, uint16):\n    A = 1\n"
    )
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"^a\.py: E: declares underlying types uint8 and uint16$"):
        Schema(package)


def test_an_enum_whose_forms_name_two_underlying_types_is_rejected(build_package):
    source = (
        HEADER
        + "class A:\n    class F(IntEnum, uint8):\n        X = 1\n    f: F\n\n"
        + "@type(cereal=False)\nclass A:\n    class F(IntEnum, uint16):\n        X = 1\n    f: F\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"^a\.py: A\.F: declares underlying types uint8 and uint16$"):
        Schema(package)


def test_an_enum_whose_members_return_in_a_later_declaration_is_one_shape(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass E(IntEnum, uint8):\n    A = 1\n\n"
        + "@type(since=3, until=4)\nclass E(IntEnum, uint8):\n    A = 1\n    B = 2\n\n"
        + "@type(since=4)\nclass E(IntEnum, uint8):\n    A = 1\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    first, _ = schema.shapes(family)

    assert first.ranges == [Range(None, 3), Range(4, None)]


def test_a_field_whose_predicate_changes_is_a_new_shape(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    a: uint8\n    b: uint8 = field(when=lambda p: p.a == 1)\n\n"
        + "@type(since=3)\nclass A:\n    a: uint8\n    b: uint8 = field(when=lambda p: p.a == 2)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert [shape.ranges for shape in schema.shapes(family)] == [[Range(None, 3)], [Range(3, None)]]


def test_a_struct_changes_shape_with_the_enum_its_predicate_names(build_package):
    source = (
        HEADER
        + "class W(IntEnum, uint8):\n    WIDTH = 8\n\n"
        + "class A:\n    a: bitset[W.WIDTH]\n    b: uint8 = field(when=lambda p: p.a.test(E.X))\n\n"
        + "class E(IntEnum, uint8):\n    X = value(1, until=3)\n    X = value(2, since=3)\n"
    )
    schema = Schema(build_package({"a": source}))
    _, _, a = schema.order

    assert [shape.ranges for shape in schema.shapes(a)] == [[Range(None, 3)], [Range(3, None)]]


def test_an_enum_a_field_codes_by_name_is_name_coded(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    X = 1\n\nclass F(IntEnum, uint8):\n    X = 1\n\n"
        + "class A:\n    x: list[E] = field(type=str)\n    y: F\n"
    )
    schema = Schema(build_package({"a": source}))
    e, _, _ = schema.order

    assert schema.name_coded == {e}


def test_an_enum_coded_by_name_inside_an_optional_is_name_coded(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    X = 1\n\nclass A:\n    x: E | None = field(type=str)\n"
    schema = Schema(build_package({"a": source}))
    e, _ = schema.order

    assert schema.name_coded == {e}


def test_an_enum_coded_by_name_in_a_dicts_scalar_half_is_name_coded(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    X = 1\n\nclass A:\n    x: dict[E, uint8] = field(type=str)\n"
    schema = Schema(build_package({"a": source}))
    e, _ = schema.order

    assert schema.name_coded == {e}


def test_a_family_reaching_a_nested_one_reaches_its_owner(build_package):
    source = HEADER + "class A:\n    x: Owner.Inner\n\nclass Owner:\n    class Inner:\n        x: uint8\n"
    schema = Schema(build_package({"a": source}))
    a = next(family for family in schema.order if family.name == "A")
    owner = next(family for family in schema.order if family.name == "Owner")

    assert roots_reached(a) == {owner}


def test_an_owner_reaches_what_its_nested_types_reach_but_not_itself(build_package):
    source = (
        HEADER
        + "class Other:\n    x: uint8\n\n"
        + "class Owner:\n    class B:\n        x: uint8\n\n    class A:\n        x: Other\n        y: B\n"
    )
    schema = Schema(build_package({"a": source}))
    other = next(family for family in schema.order if family.name == "Other")
    owner = next(family for family in schema.order if family.name == "Owner")

    assert roots_reached(owner) == {other}


def test_the_package_is_the_modules_namespace(build_package):
    schema = Schema(build_package({"a": HEADER + "class A:\n    x: uint8\n"}))

    assert (schema.package, schema.java_package, [module.stem for module in schema.modules]) == (
        "bedrock.protocol",
        "dev.endstone.protocol",
        ["a"],
    )


def test_a_duplicated_field_duplicates_only_over_its_range(build_package):
    schema = Schema(build_package({"a": SOUND}, MODELLED_INIT))
    (packet,) = schema.order

    assert [schema.shape_at(packet, version).fields[0].duplicate for version in (2168, 2225)] == [7, 1]


def test_a_change_in_duplicate_starts_a_new_shape(build_package):
    schema = Schema(build_package({"a": SOUND}, MODELLED_INIT))
    (packet,) = schema.order

    assert [shape.ranges for shape in schema.shapes(packet)] == [[Range(2168, 2225)], [Range(2225, None)]]


REORDERED = (
    HEADER
    + "@type(until=3)\nclass A:\n    x: uint8\n    y: uint16\n\n"
    + "@type(since=3)\nclass A:\n    y: uint16\n    x: uint8\n"
)

RENUMBERED = (
    HEADER
    + "class E(IntEnum, uint8):\n    A = value(1, until=3)\n    A = value(2, since=3)\n"
    + "    B = value(1, since=3)\n"
)

DISPLACED = (
    HEADER
    + "class E(IntEnum, uint8):\n    A = value(1, until=3)\n    A = value(2, since=3)\n    B = value(2, until=3)\n"
)

SIBLINGS = (
    HEADER
    + "class P:\n    class F(IntEnum, uint8):\n        A = 1\n        B = 2\n    f: F\n\n"
    + "@type(cereal=False)\nclass P:\n    class F(IntEnum, uint8):\n        B = 1\n        A = 2\n    f: F\n\n"
    + "@packet(id=1)\nclass Q:\n    p: P = field(cereal=False)\n"
)


def test_a_field_reorder_is_a_second_encoding_of_one_model(build_package):
    schema = Schema(build_package({"a": REORDERED}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_an_encoding_starts_at_the_version_that_introduced_it(build_package):
    schema = Schema(build_package({"a": REORDERED}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert [encoding.since for encoding in schema.encodings(model)] == [1, 3]


def test_a_shared_model_lists_its_slots_in_the_newest_order(build_package):
    schema = Schema(build_package({"a": REORDERED}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert [slot.name for slot in model.slots] == ["y", "x"]


def test_a_slot_type_drops_its_encoding(build_package):
    source = (
        HEADER
        + "class A:\n    x: list[uint16] = field(prefix=uint16)\n    y: uint16 = field(endian='big')\n"
        + "    z: list[uint8] = field(count=lambda p: p.y)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.slots == (
        Slot("x", List(Primitive("uint16"), None)),
        Slot("y", Primitive("uint16")),
        Slot("z", List(Primitive("uint8"), None)),
    )


def test_a_dropped_literal_keeps_the_model(build_package):
    source = HEADER + "class A:\n    flag: Literal[True] = field(until=3)\n    x: uint8\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert len(schema.models(family)) == 1


def test_a_varint_shares_the_model_of_its_fixed_width_integer(build_package):
    source = HEADER + "@type(until=3)\nclass A:\n    x: varint32\n\n@type(since=3)\nclass A:\n    x: int32\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert len(schema.models(family)) == 1


@pytest.mark.parametrize(
    ("before", "after"),
    [
        pytest.param("varint32 | None", "int32 | None", id="optional"),
        pytest.param("list[varint32]", "list[int32]", id="list"),
        pytest.param("array[varint32, 2]", "array[int32, 2]", id="array"),
        pytest.param("dict[str, varint32]", "dict[str, int32]", id="map"),
        pytest.param("varint32 | str", "int32 | str", id="variant"),
    ],
)
def test_a_container_of_a_varint_shares_the_model_of_its_fixed_width_integer(build_package, before, after):
    source = HEADER + f"@type(until=3)\nclass A:\n    x: {before}\n\n@type(since=3)\nclass A:\n    x: {after}\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert len(schema.models(family)) == 1


def test_a_field_changing_signedness_is_a_second_model(build_package):
    source = HEADER + "@type(until=3)\nclass A:\n    x: uint8\n\n@type(since=3)\nclass A:\n    x: int8\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert len(schema.models(family)) == 2


def test_a_field_typed_uint8_against_varint32_is_a_second_model(build_package):
    source = HEADER + "@type(until=3)\nclass A:\n    x: uint8\n\n@type(since=3)\nclass A:\n    x: varint32\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert len(schema.models(family)) == 2


def test_an_encoded_override_keeps_the_model(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    x: uint8\n\n@type(since=3)\nclass A:\n    x: uint8 = field(type=varint32)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert len(schema.models(family)) == 1


def test_an_encoded_override_on_an_alias_keeps_the_model(build_package):
    source = (
        HEADER
        + "type Id = uint16\n\n"
        + "@type(until=3)\nclass A:\n    x: Id\n\n@type(since=3)\nclass A:\n    x: Id = field(type=varint32)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert len(schema.models(family)) == 1


def test_a_variant_whose_cases_swap_is_a_second_model(build_package):
    source = (
        HEADER + "@type(until=3)\nclass A:\n    x: uint8 | uint16\n\n@type(since=3)\nclass A:\n    x: uint16 | uint8\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert len(schema.models(family)) == 2


def test_a_nested_type_whose_model_changes_is_a_second_owner_model(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    class B:\n        x: uint8\n\n"
        + "@type(since=3)\nclass A:\n    class B:\n        x: uint16\n"
    )
    schema = Schema(build_package({"a": source}))
    _, owner = schema.order

    assert len(schema.models(owner)) == 2


def test_a_model_held_at_some_versions_is_versioned(build_package):
    source = HEADER + "@type(until=3)\nclass A:\n    x: uint8\n\n@type(since=3)\nclass A:\n    x: int8\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert [model.versioned for model in schema.models(family)] == [True, True]


PRE_CEREAL_SINCE = (
    HEADER
    + "@type(until=3)\nclass B:\n    x: uint8\n\n@type(since=3)\nclass B:\n    x: uint16\n\n"
    + "@type(cereal=False)\nclass B:\n    x: uint16\n\n"
    + "@packet(id=1)\nclass A:\n    b: B = field(cereal=False)\n"
)


def test_each_form_lists_the_models_it_holds(build_package):
    schema = Schema(build_package({"a": PRE_CEREAL_SINCE}))
    cereal, pre_cereal, _ = schema.order

    assert (schema.models(cereal), schema.models(pre_cereal)) == (
        [schema.model_at(cereal, 1), schema.model_at(cereal, 3)],
        [schema.model_at(cereal, 3)],
    )


def test_an_enum_model_starts_at_the_version_its_family_appears(build_package):
    schema = Schema(build_package({"a": HEADER + "@type(since=3)\nclass E(IntEnum, uint8):\n    A = 1\n"}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.since == 3


def test_a_bitset_whose_width_changes_is_a_second_model(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 0\n    B = value(1, since=3)\n    COUNT = sentinel()\n\n"
        + "class A:\n    flags: bitset[E.COUNT]\n"
    )
    schema = Schema(build_package({"a": source}))
    _, family = schema.order

    assert len(schema.models(family)) == 2


def test_a_bitset_slot_is_as_wide_as_its_member_at_the_models_version(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 0\n    B = value(1, since=3)\n    COUNT = sentinel()\n\n"
        + "class A:\n    flags: bitset[E.COUNT]\n"
    )
    schema = Schema(build_package({"a": source}))
    _, family = schema.order
    model = schema.model_at(family, 3)
    (slot,) = model.slots

    assert schema.width(model, slot.type) == 2


def test_a_child_whose_encoding_changes_is_a_second_encoding_of_one_parent_model(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass B:\n    x: uint16\n\n@type(since=3)\nclass B:\n    x: uint16 = field(endian='big')\n\n"
        + "class A:\n    b: B\n"
    )
    schema = Schema(build_package({"a": source}))
    _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_parent_whose_enum_renumbers_is_one_model_with_a_second_encoding(build_package):
    schema = Schema(build_package({"a": RENUMBERED + "\nclass P:\n    e: E\n"}))
    _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


@pytest.mark.parametrize(
    ("before", "after"),
    [
        pytest.param("until=3", "since=3, type=varint32", id="another integer"),
        pytest.param("until=3, type=uint16", "since=3, type=uint16, endian='big'", id="another byte order"),
    ],
)
def test_a_parent_reading_its_enum_another_way_is_a_second_encoding(build_package, before, after):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n\n"
        + f"class P:\n    e: E = field({before})\n    e: E = field({after})\n"
    )
    schema = Schema(build_package({"a": source}))
    _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param("E | None", id="optional"),
        pytest.param("list[E]", id="list"),
        pytest.param("array[E, 2]", id="array"),
        pytest.param("dict[E, uint8]", id="map key"),
        pytest.param("dict[uint8, E]", id="map value"),
        pytest.param("uint8 | E", id="variant"),
    ],
)
def test_a_container_whose_enum_renumbers_is_one_model_with_a_second_encoding(build_package, annotation):
    schema = Schema(build_package({"a": RENUMBERED + f"\nclass P:\n    x: {annotation}\n"}))
    _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_an_encoding_reaches_each_codec_by_the_reference_its_field_holds(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n\nclass B:\n    x: uint8\n\n"
        + "class P:\n    b: B\n    e: E\n    n: E = field(type=str)\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, child, family = schema.order

    assert schema.encoding_at(family, 1).reached == {
        StructRef(child): schema.encoding_at(child, 1),
        EnumRef(enum): schema.numbering_at(enum, 1),
        EnumName(enum): schema.naming_at(enum, 1),
    }


def test_a_literal_naming_another_enums_member_is_a_second_encoding(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass E(IntEnum, uint8):\n    A = 1\n\n"
        + "@type(since=3)\nclass F(IntEnum, uint8):\n    A = 1\n\n"
        + "class P:\n    tag: Literal[E.A] = field(until=3)\n    tag: Literal[F.A] = field(since=3)\n"
    )
    schema = Schema(build_package({"a": source}))
    _, _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_condition_testing_another_field_is_a_second_encoding(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    X = 1\n\n"
        + "class P:\n    a: bitset[E.X]\n    b: bitset[E.X]\n"
        + "    y: uint8 = field(until=3, when=lambda p: p.a.test(E.X))\n"
        + "    y: uint8 = field(since=3, when=lambda p: p.b.test(E.X))\n"
    )
    schema = Schema(build_package({"a": source}))
    _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


RENAMED = HEADER + "class E(IntEnum, uint8):\n    A = value(1, 'old', until=3)\n    A = value(1, 'new', since=3)\n\n"


def test_a_parent_whose_name_coded_enum_renames_is_one_model_with_a_second_encoding(build_package):
    schema = Schema(build_package({"a": RENAMED + "class P:\n    e: E = field(type=str)\n"}))
    _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_parent_whose_name_coded_enum_gains_a_member_is_one_model_with_a_second_encoding(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = value(2, since=3)\n\n"
    schema = Schema(build_package({"a": source + "class P:\n    e: E = field(type=str)\n"}))
    _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_condition_naming_a_name_coded_enum_keeps_its_naming_in_the_encoding(build_package):
    source = RENAMED + "class P:\n    e: E = field(type=str)\n    x: uint8 = field(when=lambda p: p.e == E.A)\n"
    schema = Schema(build_package({"a": source}))
    _, family = schema.order

    assert schema.encoding_at(family, 1) is not schema.encoding_at(family, 3)


def test_an_enum_read_by_name_beside_an_integer_read_keeps_its_naming_in_the_encoding(build_package):
    schema = Schema(build_package({"a": RENAMED + "class P:\n    e: E = field(type=str)\n    f: E\n"}))
    _, family = schema.order

    assert schema.encoding_at(family, 1) is not schema.encoding_at(family, 3)


def test_a_struct_reaching_both_forms_of_a_family_keeps_the_encoding_of_each(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint16\n\n"
        + "@type(cereal=False, until=3)\nclass B:\n    x: uint16\n\n"
        + "@type(cereal=False, since=3)\nclass B:\n    x: uint16 = field(endian='big')\n\n"
        + "@packet(id=1)\nclass A:\n    c: B = field(cereal=False)\n    b: B\n"
    )
    schema = Schema(build_package({"a": source}))
    _, _, family = schema.order

    assert schema.encoding_at(family, 1) is not schema.encoding_at(family, 3)


def test_a_field_switching_to_a_sibling_with_another_encoding_is_a_second_encoding(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint16\n\n@type(cereal=False, since=3)\nclass B:\n    x: uint16 = field(endian='big')\n\n"
        + "@packet(id=1)\nclass A:\n    b: B = field(until=3)\n    b: B = field(since=3, cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    _, _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_field_whose_condition_changes_is_a_second_encoding(build_package):
    source = (
        HEADER
        + "class A:\n    k: uint8\n"
        + "    x: uint8 = field(until=3, when=lambda p: p.k == 1)\n"
        + "    x: uint8 = field(since=3, when=lambda p: p.k == 2)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_condition_whose_operator_changes_is_a_second_encoding(build_package):
    source = (
        HEADER
        + "class A:\n    k: uint8\n"
        + "    x: uint8 = field(until=3, when=lambda p: p.k == 1)\n"
        + "    x: uint8 = field(since=3, when=lambda p: p.k != 1)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_negated_condition_is_a_second_encoding(build_package):
    source = (
        HEADER
        + "class A:\n    k: uint8\n"
        + "    x: uint8 = field(until=3, when=lambda p: p.k == 1)\n"
        + "    x: uint8 = field(since=3, when=lambda p: not p.k == 1)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_list_whose_length_prefix_changes_is_a_second_encoding(build_package):
    source = (
        HEADER + "class A:\n    x: list[uint8] = field(until=3)\n    x: list[uint8] = field(since=3, prefix=uint16)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_list_whose_count_changes_is_a_second_encoding(build_package):
    source = (
        HEADER
        + "class A:\n    n: uint16\n    m: uint16\n"
        + "    x: list[uint8] = field(until=3, count=lambda p: p.n)\n"
        + "    x: list[uint8] = field(since=3, count=lambda p: p.m)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_uuid_read_as_text_keeps_the_model(build_package):
    source = (
        HEADER
        + "import uuid\n\n"
        + "class A:\n    x: uuid.UUID = field(until=3)\n    x: uuid.UUID = field(since=3, type=str)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert len(schema.models(family)) == 1


def test_a_field_whose_copies_change_is_a_second_encoding(build_package):
    source = HEADER + "class A:\n    x: uint8 = field(until=3)\n    x: uint8 = field(since=3, duplicate=2)\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_pre_cereal_sibling_with_equal_members_shares_the_cereal_model(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint16\n\n@type(cereal=False)\nclass B:\n    x: uint16 = field(endian='big')\n\n"
        + "@packet(id=1)\nclass A:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, pre_cereal, _ = schema.order

    assert schema.model_at(pre_cereal, 1) is schema.model_at(cereal, 1)


def test_a_pre_cereal_sibling_with_an_equal_encoding_shares_it(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint16\n\n@type(cereal=False)\nclass B:\n    x: uint16\n\n"
        + "@packet(id=1)\nclass A:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, pre_cereal, _ = schema.order

    assert list(schema.encoding_at(cereal, 1).runs) == [cereal, pre_cereal]


def test_a_pre_cereal_sibling_naming_its_own_sibling_child_shares_the_encoding(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint16\n\n@type(cereal=False)\nclass B:\n    x: uint16\n\n"
        + "class A:\n    b: B\n\n@type(cereal=False)\nclass A:\n    b: B = field(cereal=False)\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    _, _, cereal, pre_cereal, _ = schema.order

    assert schema.encoding_at(pre_cereal, 1) is schema.encoding_at(cereal, 1)


NESTED = (
    HEADER
    + "class A:\n    class F(IntEnum, uint8):\n        X = 1\n        Y = 2\n    {fields}\n\n"
    + "@type(cereal=False)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n        Y = 3\n    {fields}\n\n"
    + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False)\n"
)


def test_a_pre_cereal_sibling_whose_nested_enum_numbers_differently_shares_the_cereal_model(build_package):
    schema = Schema(build_package({"a": NESTED.format(fields="f: F")}))
    _, cereal, _, pre_cereal, _ = schema.order

    assert schema.model_at(pre_cereal, 1) is schema.model_at(cereal, 1)


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param("f: F", id="enum field"),
        pytest.param("fs: list[F]", id="list of enums"),
        pytest.param("f: F\n    y: uint8 = field(when=lambda p: p.f == F.X)", id="condition"),
        pytest.param("f: F\n    y: uint8 = field(when=lambda p: not p.f == F.X)", id="negated condition"),
        pytest.param(
            "f: F\n    k: uint8\n    y: uint8 = field(when=lambda p: p.f == F.X and p.k == 1)", id="conjunction"
        ),
    ],
)
def test_a_pre_cereal_sibling_reading_its_nested_enum_by_its_own_numbers_has_its_own_encoding(build_package, fields):
    schema = Schema(build_package({"a": NESTED.format(fields=fields)}))
    _, cereal, _, pre_cereal, _ = schema.order

    assert schema.encoding_at(pre_cereal, 1) is not schema.encoding_at(cereal, 1)


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param("f: F = field(type=str)", id="name-coded field"),
        pytest.param("tag: Literal[F.X]", id="literal"),
        pytest.param("bits: bitset[F.X]", id="bitset"),
        pytest.param("bits: bitset[F.X]\n    y: uint8 = field(when=lambda p: p.bits.test(F.X))", id="test"),
    ],
)
def test_a_pre_cereal_sibling_coding_its_nested_enum_alike_reuses_the_cereal_encoding(build_package, fields):
    schema = Schema(build_package({"a": NESTED.format(fields=fields)}))
    _, cereal, _, pre_cereal, _ = schema.order

    assert schema.encoding_at(pre_cereal, 1) is schema.encoding_at(cereal, 1)


def test_a_slot_reference_resolves_to_the_model_of_the_form_it_names(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    x: uint16\n\n"
        + "@packet(id=1)\nclass A:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    _, pre_cereal, family = schema.order
    model = schema.model_at(family, 1)
    (slot,) = model.slots

    assert schema.target(model, slot.type) is schema.model_at(pre_cereal, 1)


def test_a_nested_model_is_owned_by_the_newest_owner_model_that_holds_it(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    class B:\n        x: uint8\n    b: B\n\n"
        + "@type(since=3)\nclass A:\n    class B:\n        x: uint8\n    b: B\n    y: uint8\n"
    )
    schema = Schema(build_package({"a": source}))
    nested, owner = schema.order
    (inner,) = schema.models(nested)

    assert schema.owner(inner) is schema.models(owner)[1]


def test_a_model_held_at_every_version_is_unversioned(build_package):
    schema = Schema(build_package({"a": HEADER + "class A:\n    x: uint8\n"}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.versioned is False


def test_the_registry_holds_the_packet_live_at_each_version(build_package):
    source = (
        HEADER
        + "@packet(id=7, until=3)\nclass P:\n    x: uint8\n\n"
        + "@packet(id=7, since=3)\nclass Q:\n    x: uint8\n"
    )
    schema = Schema(build_package({"a": source}))
    p, q = schema.order

    assert (schema.packets(1)[7].model.family, schema.packets(3)[7].model.family) == (p, q)


def test_an_enum_whose_members_change_is_one_model(build_package):
    schema = Schema(build_package({"a": HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = value(2, since=3)\n"}))
    (family,) = schema.order

    assert len(schema.models(family)) == 1


def test_a_member_added_with_stable_numbers_is_a_second_numbering(build_package):
    schema = Schema(build_package({"a": HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = value(2, since=3)\n"}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1) is not schema.numbering_at(family, 3)


def test_versions_with_equal_numbers_and_members_share_a_numbering(build_package):
    schema = Schema(build_package({"a": HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = value(2, since=3)\n"}))
    (family,) = schema.order

    assert schema.numbering_at(family, 3) is schema.numbering_at(family, 5)


def test_an_enum_model_lists_the_newest_declarations_members_first(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass E(IntEnum, uint8):\n    A = 1\n    B = 2\n\n"
        + "@type(since=3)\nclass E(IntEnum, uint8):\n    C = 3\n    A = 1\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert [member.name for member in model.members] == ["C", "A", "B"]


def test_a_union_member_is_deprecated_as_its_newest_declaration_says(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = value(1, until=3)\n"
        + "    A = value(1, since=3, deprecated=True)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert [member.deprecated for member in model.members] == [True]


def test_a_renumbered_member_is_a_second_numbering(build_package):
    schema = Schema(build_package({"a": RENUMBERED}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1) is not schema.numbering_at(family, 3)


def test_a_member_whose_number_another_member_holds_takes_the_next_free_value(build_package):
    schema = Schema(build_package({"a": DISPLACED}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"A": 2, "B": 3}


def test_a_renumbering_pairs_each_number_it_displaces_with_the_value_it_frees(build_package):
    schema = Schema(build_package({"a": DISPLACED}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1).encoded == {1: 3, 2: 1, 3: 2}


def test_a_numbering_is_the_identity_only_when_it_moves_no_value(build_package):
    schema = Schema(build_package({"a": RENUMBERED}))
    (family,) = schema.order

    assert (schema.numbering_at(family, 1).identity, schema.numbering_at(family, 3).identity) == (False, True)


DERIVED = (
    HEADER
    + "class E(IntEnum, uint8):\n    A = 0\n    with value(since=3):\n        B = auto()\n    COUNT = auto()\n"
    + "    LATEST = COUNT - 1\n"
)


def test_a_numbering_lacking_a_member_is_not_the_identity(build_package):
    schema = Schema(build_package({"a": GROWING}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1).identity is False


def test_a_member_value_no_member_holds_at_a_version_is_absent_there(build_package):
    schema = Schema(build_package({"a": GROWING}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1).absent == {2}


def test_a_member_value_no_member_numbers_at_a_version_is_lossy_there(build_package):
    schema = Schema(build_package({"a": GROWING}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1).lossy == {2}


def test_a_member_encodes_to_its_number_where_it_differs_from_its_value(build_package):
    schema = Schema(build_package({"a": DERIVED}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1).encoded.get(2) == 1


def test_a_number_decodes_to_the_value_of_the_member_holding_it(build_package):
    schema = Schema(build_package({"a": DERIVED}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1).decoded.get(1) == 2


def test_a_number_a_pointer_shares_decodes_to_the_pointers_value(build_package):
    schema = Schema(build_package({"a": DERIVED}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1).decoded.get(0) == 1


def test_a_pointer_ranks_first_among_the_members_sharing_its_value(build_package):
    schema = Schema(build_package({"a": DERIVED}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert [member.name for member in model.members] == ["A", "LATEST", "B", "COUNT"]


def test_a_synonym_ranks_after_the_member_it_repeats(build_package):
    schema = Schema(
        build_package({"a": HEADER + "class E(IntEnum, uint8):\n    A = value(1, synonym=True)\n    B = 1\n"})
    )
    (family,) = schema.order
    (model,) = schema.models(family)

    assert [member.name for member in model.members] == ["B", "A"]


def test_pointers_numbered_alike_at_one_version_only_are_rejected(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n    B = value(2, since=3)\n"
        + "    COUNT = auto()\n    X = A\n    Y = COUNT - 1\n"
    )
    message = r"^a\.py: E\.Y: is numbered 1 at 1 and X 1, but they hold two library values$"

    with pytest.raises(CompilerError, match=message):
        Schema(build_package({"a": source}))


def test_a_derived_value_no_member_holds_encodes_to_the_derived_members_number(build_package):
    schema = Schema(build_package({"a": DERIVED}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1).encoded.get(1) == 0


def test_a_derived_value_no_member_holds_is_not_absent(build_package):
    schema = Schema(build_package({"a": DERIVED}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1).absent == frozenset()


def test_a_number_no_member_value_holds_pairs_with_the_first_unused_value_both_ways(build_package):
    schema = Schema(build_package({"a": DISPLACED}))
    (family,) = schema.order
    numbering = schema.numbering_at(family, 1)

    assert (numbering.encoded[1], numbering.decoded[3]) == (3, 1)


def test_an_unused_value_left_with_no_free_number_is_lossy(build_package):
    schema = Schema(build_package({"a": DERIVED}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1).lossy == {2}


def test_free_numbers_pair_with_unused_values_in_ascending_order(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = value(1, until=3)\n    A = value(3, since=3)\n"
        + "    B = value(2, until=3)\n    B = value(4, since=3)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    numbering = schema.numbering_at(family, 1)

    assert (numbering.encoded.get(1), numbering.encoded.get(2)) == (3, 4)


def test_a_derived_value_numbered_as_itself_has_no_encoded_entry(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass E(IntEnum, uint8):\n    M = 1\n    D = M\n\n"
        + "@type(since=3)\nclass E(IntEnum, uint8):\n    T = 1\n    M = 5\n    D = T\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1).encoded == {5: 1}


def test_a_paired_value_is_not_lossy(build_package):
    schema = Schema(build_package({"a": DISPLACED}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1).lossy == frozenset()


def test_numberings_lists_a_models_numberings_in_version_order(build_package):
    schema = Schema(build_package({"a": RENUMBERED}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert schema.numberings(model) == [schema.numbering_at(family, 1), schema.numbering_at(family, 3)]


def test_numberings_lists_the_numberings_of_both_forms_in_version_order(build_package):
    source = (
        HEADER
        + "@type(since=3)\nclass P:\n    class F(IntEnum, uint8):\n        A = 1\n        B = 2\n    f: F\n\n"
        + "@type(cereal=False)\nclass P:\n    class F(IntEnum, uint8):\n        B = 1\n        A = 2\n    f: F\n\n"
        + "@packet(id=1)\nclass Q:\n    p: P = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, pre_cereal, _, _ = schema.order
    (model,) = schema.models(cereal)

    assert schema.numberings(model) == [schema.numbering_at(pre_cereal, 1), schema.numbering_at(cereal, 3)]


def test_a_derived_member_whose_value_another_member_holds_with_another_number_is_rejected(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass E(IntEnum, uint8):\n    A = 1\n    B = 2\n    X = A\n\n"
        + "@type(since=3)\nclass E(IntEnum, uint8):\n    A = 1\n    B = 2\n    X = B\n"
    )
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"^a\.py: E\.X: is numbered 1 at 1, where B holds its value with 2$"):
        Schema(package)


def test_a_library_value_is_the_members_number_at_the_newest_version(build_package):
    schema = Schema(build_package({"a": RENUMBERED}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"A": 2, "B": 1}


def test_names_that_never_coexist_share_their_number_as_a_value(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    A = value(5, until=3)\n    B = value(5, since=3)\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"A": 5, "B": 5}


def test_members_numbered_alike_share_a_value(build_package):
    schema = Schema(
        build_package({"a": HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = value(1, synonym=True)\n"})
    )
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"A": 1, "B": 1}


def test_an_alias_is_its_expression_over_library_values(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass E(IntEnum, uint8):\n    A = 1\n    B = 2\n    LAST = B\n\n"
        + "@type(since=3)\nclass E(IntEnum, uint8):\n    A = 2\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values["LAST"] == 3


def test_an_alias_of_a_sentinel_takes_its_number_where_it_is_newest(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n    B = value(2, since=3)\n"
        + "    COUNT = sentinel()\n    LATEST = COUNT - 1\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values["LATEST"] == 2


@pytest.mark.parametrize(
    ("underlying", "highest"),
    [pytest.param("uint8", 255, id="unsigned"), pytest.param("int8", 127, id="signed")],
)
def test_a_member_with_no_free_library_value_in_its_underlying_type_is_rejected(build_package, underlying, highest):
    source = (
        HEADER
        + f"class E(IntEnum, {underlying}):\n    A = value({highest - 1}, until=3)\n    A = value({highest}, since=3)\n"
        + f"    B = value({highest}, until=3)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(
        CompilerError, match=rf"a\.py: E\.B: has no library value above {highest} that fits {underlying}"
    ):
        Schema(package)


def test_a_library_value_error_names_a_nested_enum_by_its_owner(build_package):
    source = (
        HEADER
        + "class A:\n    class E(IntEnum, uint8):\n        A = value(254, until=3)\n        A = value(255, since=3)\n"
        + "        B = value(255, until=3)\n    e: E\n"
    )
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"a\.py: A\.E\.B: has no library value above 255 that fits uint8"):
        Schema(package)


def test_library_values_that_do_not_number_one_to_one_are_rejected(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n    B = value(1, until=3, synonym=True)\n    B = value(2, since=3)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"a\.py: E: does not number its library values one to one at 1"):
        Schema(package)


def test_a_one_to_one_error_names_a_nested_enum_by_its_owner(build_package):
    source = (
        HEADER
        + "class A:\n    class E(IntEnum, uint8):\n        A = 1\n        B = value(1, until=3, synonym=True)\n"
        + "        B = value(2, since=3)\n    e: E\n"
    )
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"a\.py: A\.E: does not number its library values one to one at 1"):
        Schema(package)


def test_a_member_beside_a_holder_at_an_older_version_takes_the_next_free_value(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    O = value(8, until=2)\n    O = value(7, since=5)\n    M = value(7, until=4)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"O": 7, "M": 8}


def test_an_older_version_does_not_move_a_value_given_at_a_newer_one(build_package):
    schema = Schema(build_package({"a": DISPLACED + "    C = value(200, until=2)\n"}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"A": 2, "B": 3, "C": 200}


def test_a_free_value_is_above_the_sentinel_numbers_seen(build_package):
    schema = Schema(build_package({"a": DISPLACED + "    COUNT = sentinel()\n"}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"A": 2, "B": 4}


def test_a_member_of_both_forms_takes_the_cereal_forms_number(build_package):
    schema = Schema(build_package({"a": SIBLINGS}))
    cereal, _, _, _, _ = schema.order

    assert schema.models(cereal)[0].values == {"A": 1, "B": 2}


def test_a_sibling_form_has_its_own_numbering(build_package):
    schema = Schema(build_package({"a": SIBLINGS}))
    _, _, pre_cereal, _, _ = schema.order

    assert schema.numbering_at(pre_cereal, 1).encoded == {1: 2, 2: 1}


def test_members_numbered_alike_share_the_free_value_a_displacement_gives_them(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    H = value(1, until=3)\n    H = value(2, since=3)\n"
        + "    X = value(2, until=3)\n    Y = value(2, until=3, synonym=True)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"H": 2, "X": 3, "Y": 3}


def test_members_renumbered_alike_share_a_value(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    X = value(3, until=3)\n"
        + "    X = value(5, since=3)\n    Y = value(3, until=3, synonym=True)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"X": 5, "Y": 5}


def test_a_member_numbered_like_a_renumbered_member_takes_its_value(build_package):
    source = (
        HEADER
        + "class E(IntEnum, int32):\n    A = 0\n    B = value(1, since=3)\n    TOTAL = value(1, until=3)\n"
        + "    TOTAL = value(2, since=3)\n    INVALID = value(1, until=3, synonym=True)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"A": 0, "B": 1, "TOTAL": 2, "INVALID": 2}


def test_a_free_value_may_be_the_highest_its_underlying_type_holds(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = value(253, until=3)\n    A = value(254, since=3)\n"
        + "    B = value(254, until=3)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"A": 254, "B": 255}


def test_a_second_free_value_past_the_highest_is_rejected_after_one_at_the_highest(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = value(253, until=3)\n    A = value(254, since=3)\n"
        + "    B = value(254, until=3)\n"
        + "    C = value(1, until=2)\n    C = value(2, since=2)\n    D = value(2, until=2)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"a\.py: E\.D: has no library value above 255 that fits uint8"):
        Schema(package)


def test_two_free_values_differ(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = value(1, until=3)\n    A = value(2, since=3)\n"
        + "    B = value(2, since=2, until=3)\n    C = value(3, until=2)\n    C = value(4, since=2)\n"
        + "    D = value(4, until=2)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"A": 2, "B": 5, "C": 4, "D": 6}


def test_an_alias_of_a_sentinel_takes_no_free_value(build_package):
    source = (
        DISPLACED
        + "    COUNT = sentinel()\n    with value(since=3):\n        LAST = COUNT - 1\n    Z = value(9, until=3)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"A": 2, "B": 10, "LAST": 2, "Z": 9}


def test_names_that_never_coexist_keep_their_own_numbers_as_values(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    A = value(1, until=3)\n    B = value(2, since=3)\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"A": 1, "B": 2}


def test_members_numbered_alike_at_every_place_both_are_live_share_a_value(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    X = value(3, until=2)\n"
        + "    X = value(5, since=4)\n    Y = value(3, until=4, synonym=True)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"X": 5, "Y": 5}


def test_a_member_numbered_alike_at_other_versions_takes_no_free_value(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    X = value(5, until=2)\n    X = value(255, since=4)\n"
        + "    H = value(6, until=4)\n    H = value(5, since=4)\n    Y = value(5, until=4, synonym=True)\n"
        + "    C = value(1, until=2)\n    C = value(2, since=2)\n    D = value(2, until=2)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"a\.py: E\.D: has no library value above 255 that fits uint8"):
        Schema(package)


def test_a_member_numbered_alike_to_a_displaced_one_takes_no_free_value(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    H = value(253, until=3)\n    H = value(254, since=3)\n"
        + "    X = value(254, until=3)\n    Y = value(254, until=3, synonym=True)\n"
        + "    C = value(1, until=2)\n    C = value(2, since=2)\n    D = value(2, until=2)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"a\.py: E\.D: has no library value above 255 that fits uint8"):
        Schema(package)


def test_an_alias_holds_no_value_a_member_can_clash_with(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    R = value(7, since=3)\n"
        + "    Z = 9\n    L = value(9, until=3, synonym=True)\n    with value(since=3):\n        L = R\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"R": 7, "Z": 9, "L": 7}


def test_a_member_beside_the_second_holder_of_a_value_with_no_room_is_rejected(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    X = value(255, since=4)\n    Z = value(255, since=3, until=4)\n"
        + "    Z = value(254, until=2)\n    Y = value(255, until=3)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"a\.py: E\.Y: has no library value above 255 that fits uint8"):
        Schema(package)


def test_a_free_value_is_above_the_numbers_at_its_own_version(build_package):
    schema = Schema(build_package({"a": DISPLACED + "    C = value(200, until=3)\n"}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values == {"A": 2, "B": 201, "C": 200}


def test_a_member_beside_a_holder_only_at_an_older_version_with_no_room_is_rejected(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    O = value(254, until=2)\n    O = value(255, since=5)\n"
        + "    M = value(255, until=4)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"a\.py: E\.M: has no library value above 255 that fits uint8"):
        Schema(package)


def test_a_model_marks_the_members_its_newest_declaration_derives(build_package):
    schema = Schema(build_package({"a": DERIVED}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.derived == {"LATEST"}


def test_an_alias_subtracts_its_offset(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    A = 0\n    COUNT = 1\n    LAST = COUNT - 1\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert model.values["LAST"] == 0


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param("tag: Literal[E.X]", id="literal"),
        pytest.param("bits: bitset[E.X]\n    y: uint8 = field(when=lambda p: p.bits.test(E.X))", id="test"),
        pytest.param("bits: bitset[E.X]", id="width"),
    ],
)
def test_an_encoding_numbers_a_member_its_fields_name_at_its_version(build_package, fields):
    source = HEADER + "class E(IntEnum, uint8):\n    X = value(1, until=3)\n    X = value(2, since=3)\n\n"
    schema = Schema(build_package({"a": source + f"class P:\n    {fields}\n"}))
    enum, family = schema.order

    assert schema.encoding_at(family, 3).numbers.get(MemberRef(enum, "X")) == 2


def test_an_encoding_does_not_number_a_member_a_condition_compares(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    X = value(1, until=3)\n    X = value(2, since=3)\n\n"
        + "class P:\n    k: E\n    y: uint8 = field(when=lambda p: p.k == E.X)\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, family = schema.order

    assert MemberRef(enum, "X") not in schema.encoding_at(family, 3).numbers


def test_a_condition_compares_a_sentinel_as_the_value_its_number_decodes_to(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    B = value(1, until=3)\n    B = value(2, since=3)\n    A = 0\n"
        + "    COUNT = sentinel()\n\n"
        + "class P:\n    k: E\n    y: uint8 = field(when=lambda p: p.k == E.COUNT)\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, family = schema.order

    assert schema.encoding_at(family, 1).numbers.get(MemberRef(enum, "COUNT")) == 2


def test_a_condition_on_a_sentinel_whose_number_decodes_to_no_value_is_rejected(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 0\n    X = value(1, since=3)\n    B = value(1, until=3)\n"
        + "    B = value(2, since=3)\n    COUNT = sentinel()\n\n"
        + "class P:\n    k: E\n    y: uint8 = field(when=lambda p: p.k == E.COUNT)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(
        CompilerError, match=r"^a\.py: P\.y: compares E\.COUNT, numbered 2 at 1, which decodes to no value$"
    ):
        Schema(package)


def test_a_condition_on_a_name_coded_member_keys_on_its_value(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    X = value(1, until=3)\n    X = value(2, since=3)\n    Y = 3\n\n"
        + "class P:\n    e: E = field(type=str)\n    y: uint8 = field(when=lambda p: p.e == E.X)\n"
    )
    schema = Schema(build_package({"a": source}))
    _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 1


def test_a_condition_on_a_sentinel_whose_number_alone_moves_is_a_second_encoding(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n    with value(until=3):\n        B = sentinel()\n"
        + "    COUNT = sentinel()\n\n"
        + "class P:\n    k: E\n    y: uint8 = field(when=lambda p: p.k == E.COUNT)\n"
    )
    schema = Schema(build_package({"a": source}))
    _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_literal_whose_member_is_renumbered_is_a_second_encoding(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    X = value(1, until=3)\n    X = value(2, since=3)\n\n"
    schema = Schema(build_package({"a": source + "class P:\n    tag: Literal[E.X]\n"}))
    _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_derived_member_resolves_to_the_member_numbered_like_it_at_the_version(build_package):
    schema = Schema(build_package({"a": DERIVED}))
    (family,) = schema.order

    assert schema.resolve(MemberRef(family, "LATEST"), 1) == MemberRef(family, "A")


def test_a_member_that_is_not_derived_resolves_to_itself(build_package):
    schema = Schema(build_package({"a": DERIVED}))
    (family,) = schema.order

    assert schema.resolve(MemberRef(family, "COUNT"), 1) == MemberRef(family, "COUNT")


def test_a_numbering_that_leaves_and_returns_is_one_numbering_with_two_runs(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 0\n    B = value(1, until=3)\n    B = value(2, since=3, until=4)\n"
        + "    B = value(1, since=4)\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert schema.numbering_at(family, 1).runs == [Range(None, 3), Range(4, None)]


SENTINEL = HEADER + "class E(IntEnum, uint8):\n    A = 0\n    B = value(1, since=3)\n    COUNT = sentinel()\n\n"


def test_a_literal_naming_a_sentinel_whose_number_changes_is_a_second_encoding(build_package):
    schema = Schema(build_package({"a": SENTINEL + "class P:\n    tag: Literal[E.COUNT]\n"}))
    _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_test_reading_a_sentinel_whose_number_changes_is_a_second_encoding(build_package):
    source = (
        SENTINEL
        + "class W(IntEnum, uint8):\n    WIDTH = 8\n\n"
        + "class P:\n    bits: bitset[W.WIDTH]\n    x: uint8 = field(when=lambda p: p.bits.test(E.COUNT))\n"
    )
    schema = Schema(build_package({"a": source}))
    _, _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


def test_a_name_coded_enum_whose_names_change_is_a_second_naming(build_package):
    schema = Schema(build_package({"a": RENAMED + "class P:\n    e: E = field(type=str)\n"}))
    enum, _ = schema.order

    assert schema.naming_at(enum, 1) is not schema.naming_at(enum, 3)


def test_a_name_coded_enum_whose_members_only_reorder_keeps_its_naming(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass E(IntEnum, uint8):\n    A = 1\n    B = 2\n\n"
        + "@type(since=3)\nclass E(IntEnum, uint8):\n    B = 2\n    A = 1\n\n"
        + "class P:\n    e: E = field(type=str)\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, _ = schema.order

    assert schema.naming_at(enum, 1) is schema.naming_at(enum, 3)


def test_a_name_coded_enum_whose_members_sharing_a_value_reorder_is_a_second_naming(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass E(IntEnum, uint8):\n    A = 1\n    B = value(1, synonym=True)\n\n"
        + "@type(since=3)\nclass E(IntEnum, uint8):\n    B = 1\n    A = value(1, synonym=True)\n\n"
        + "class P:\n    e: E = field(type=str)\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, _ = schema.order

    assert schema.naming_at(enum, 1) is not schema.naming_at(enum, 3)


def test_a_name_coded_enum_keeps_its_naming_while_each_value_writes_its_first_name(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass E(IntEnum, uint8):\n    A = 1\n"
        + "    B = value(1, synonym=True)\n    C = value(1, synonym=True)\n\n"
        + "@type(since=3)\nclass E(IntEnum, uint8):\n    A = 1\n"
        + "    C = value(1, synonym=True)\n    B = value(1, synonym=True)\n\n"
        + "class P:\n    e: E = field(type=str)\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, _ = schema.order

    assert schema.naming_at(enum, 1) is schema.naming_at(enum, 3)


def test_a_name_coded_enum_whose_unwritten_name_changes_is_a_second_naming(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n    B = value(1, 'old', until=3, synonym=True)\n"
        + "    B = value(1, 'new', since=3, synonym=True)\n\n"
        + "class P:\n    e: E = field(type=str)\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, _ = schema.order

    assert schema.naming_at(enum, 1) is not schema.naming_at(enum, 3)


def test_a_name_coded_enum_whose_alias_becomes_a_member_is_a_second_naming(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass E(IntEnum, uint8):\n    A = 1\n    B = A\n\n"
        + "@type(since=3)\nclass E(IntEnum, uint8):\n    A = 1\n    B = value(1, synonym=True)\n\n"
        + "class P:\n    e: E = field(type=str)\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, _ = schema.order

    assert schema.naming_at(enum, 1) is not schema.naming_at(enum, 3)


def test_a_value_is_written_with_the_first_name_its_number_takes_at_the_version(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass E(IntEnum, uint8):\n    A = 1\n    B = 2\n    X = A\n\n"
        + "@type(since=3)\nclass E(IntEnum, uint8):\n    A = 1\n    B = 2\n\n"
        + "class P:\n    e: E = field(type=str)\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, _ = schema.order

    assert schema.naming_at(enum, 1).written == {1: "x", 2: "b"}


def test_a_naming_reads_each_live_name_as_its_members_value(build_package):
    schema = Schema(build_package({"a": RENAMED + "class P:\n    e: E = field(type=str)\n"}))
    enum, _ = schema.order

    assert schema.naming_at(enum, 1).read == {"old": 1}


def test_a_derived_value_no_member_holds_is_written_with_the_derived_name(build_package):
    schema = Schema(build_package({"a": DERIVED + "\nclass P:\n    e: E = field(type=str)\n"}))
    enum, _ = schema.order

    assert schema.naming_at(enum, 1).written.get(1) == "latest"


def test_a_pointers_name_reads_as_the_pointers_value(build_package):
    schema = Schema(build_package({"a": DERIVED + "\nclass P:\n    e: E = field(type=str)\n"}))
    enum, _ = schema.order

    assert schema.naming_at(enum, 1).read.get("latest") == 1


def test_a_value_is_written_with_the_name_of_the_member_a_synonym_repeats(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = value(1, synonym=True)\n"
        + "    B = 1\n\nclass P:\n    e: E = field(type=str)\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, _ = schema.order

    assert schema.naming_at(enum, 1).written == {1: "b"}


def test_the_first_of_two_pointers_numbered_alike_is_written(build_package):
    source = (
        HEADER + "class E(IntEnum, uint8):\n    A = 1\n    X = A\n    Y = A\n\nclass P:\n    e: E = field(type=str)\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, _ = schema.order

    assert schema.naming_at(enum, 1).written == {1: "x"}


def test_namings_lists_a_models_namings_in_version_order(build_package):
    schema = Schema(build_package({"a": RENAMED + "class P:\n    e: E = field(type=str)\n"}))
    enum, _ = schema.order
    (model,) = schema.models(enum)

    assert schema.namings(model) == [schema.naming_at(enum, 1), schema.naming_at(enum, 3)]


def test_namings_lists_the_namings_of_both_forms_in_version_order(build_package):
    source = (
        HEADER
        + "@type(since=3)\nclass P:\n    class F(IntEnum, uint8):\n        A = 1\n    f: F = field(type=str)\n\n"
        + "@type(cereal=False)\nclass P:\n    class F(IntEnum, uint8):\n        A = 1\n        B = 2\n"
        + "    f: F = field(type=str)\n\n"
        + "@packet(id=1)\nclass Q:\n    p: P = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, pre_cereal, _, _ = schema.order
    (model,) = schema.models(cereal)

    assert schema.namings(model) == [schema.naming_at(pre_cereal, 1), schema.naming_at(cereal, 3)]


def test_an_enum_no_field_codes_by_name_has_no_naming(build_package):
    schema = Schema(build_package({"a": GROWING}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert schema.namings(model) == []


@pytest.mark.parametrize(
    ("members", "message"),
    [
        pytest.param(
            "    A = value(0, since=3)\n    B = 1\n    COUNT = 2\n",
            r"^a\.py: E: lacks A at 1, below a bitset width$",
            id="a member absent",
        ),
        pytest.param(
            "    A = 0\n    B = value(1, until=3)\n    B = value(2, since=3)\n    C = value(1, since=3)\n"
            "    COUNT = 3\n",
            r"^a\.py: E: numbers B 1 at 1, not its value 2, below a bitset width$",
            id="a member numbered off its value",
        ),
        pytest.param(
            "    A = 0\n    X = value(1, until=3)\n    X = value(5, since=3)\n    COUNT = value(2, until=3)\n"
            "    COUNT = value(6, since=3)\n",
            r"^a\.py: E: numbers X 1 at 1, not its value 5, below a bitset width$",
            id="a member numbered below the width from a value above it",
        ),
    ],
)
def test_a_bitset_width_enum_not_numbering_a_member_below_the_width_as_its_value_is_rejected(
    build_package, members, message
):
    source = HEADER + "class E(IntEnum, uint8):\n" + members + "\nclass P:\n    flags: bitset[E.COUNT]\n"
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=message):
        Schema(package)


@pytest.mark.parametrize(
    ("annotation", "predicate"),
    [
        pytest.param("uint8", "p.a == E.X", id="an integer"),
        pytest.param("F", "p.a == E.X", id="another enum"),
        pytest.param("E", "E.X", id="nothing"),
        pytest.param("uint8", "not p.a == E.X", id="a negation"),
        pytest.param("uint8", "p.a == 1 and p.a == E.X", id="a conjunction"),
    ],
)
def test_a_condition_comparing_a_member_with_a_field_of_another_type_is_rejected(build_package, annotation, predicate):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    X = 1\n\nclass F(IntEnum, uint8):\n    X = 1\n\n"
        + f"class P:\n    a: {annotation}\n    b: uint8 = field(when=lambda p: {predicate})\n"
    )
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"^a\.py: P\.b: compares E\.X with a value of another type$"):
        Schema(package)


def test_a_condition_comparing_a_field_with_a_member_of_its_sibling_form_is_accepted(build_package):
    source = (
        HEADER
        + "class A:\n    class F(IntEnum, uint8):\n        X = 1\n        Y = 2\n    f: F\n\n"
        + "@type(cereal=False)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n        Y = 3\n    f: F\n"
        + "    y: uint8 = field(when=lambda p: p.f == A.F.X)\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    _, _, _, pre_cereal, _ = schema.order

    assert len(schema.models(pre_cereal)) == 1


@pytest.mark.parametrize(
    "predicate",
    [
        pytest.param("p.k == 1", id="an integer"),
        pytest.param("p.k & 1", id="a mask"),
        pytest.param("p.k < E.Y", id="an order"),
        pytest.param("not p.k", id="its truth"),
    ],
)
def test_a_condition_reading_an_enum_as_a_number_where_a_value_moves_is_rejected(build_package, predicate):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    X = value(1, until=3)\n    X = value(2, since=3)\n    Y = 3\n\n"
        + f"class P:\n    k: E\n    b: uint8 = field(when=lambda p: {predicate})\n"
    )
    package = build_package({"a": source})

    with pytest.raises(
        CompilerError, match=r"^a\.py: P\.b: reads k as a number at 1, where E numbers a value apart from it$"
    ):
        Schema(package)


def test_a_condition_reading_an_enum_as_a_number_is_accepted_where_only_members_are_missing(build_package):
    source = GROWING + "\nclass P:\n    k: E\n    b: uint8 = field(when=lambda p: p.k == 1)\n"
    schema = Schema(build_package({"a": source}))
    enum, _ = schema.order

    assert schema.numbering_at(enum, 1).absent == {2}


def test_a_derived_member_below_a_bitset_width_may_be_numbered_apart_from_its_value(build_package):
    schema = Schema(build_package({"a": DERIVED + "\nclass P:\n    flags: bitset[E.COUNT]\n"}))
    _, family = schema.order
    model = schema.model_at(family, 1)
    (slot,) = model.slots

    assert schema.width(model, slot.type) == 1


def test_a_condition_on_an_enum_encoding_a_derived_value_to_another_members_number_is_rejected(build_package):
    package = build_package({"a": DERIVED + "\nclass P:\n    e: E\n    x: uint8 = field(when=lambda p: p.e == E.A)\n"})

    with pytest.raises(
        CompilerError, match=r"^a\.py: P\.x: compares a value of E at 1, where LATEST encodes to A's number$"
    ):
        Schema(package)


def test_a_dict_keyed_by_an_enum_encoding_a_derived_value_to_another_members_number_is_rejected(build_package):
    package = build_package({"a": DERIVED + "\nclass P:\n    m: dict[E, uint8]\n"})

    with pytest.raises(CompilerError, match=r"^a\.py: E: keys a dict at 1, where LATEST encodes to A's number$"):
        Schema(package)


@pytest.mark.parametrize("version", [1, 3, 5])
def test_enum_type_is_the_family_model_at_every_version_when_a_number_moves(build_package, version):
    schema = Schema(build_package({"a": RENUMBERED}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert schema.enum_type(family, version) is model


def test_an_enum_slots_target_is_the_model_of_a_renumbered_family(build_package):
    schema = Schema(build_package({"a": RENUMBERED + "\nclass P:\n    e: E\n"}))
    enum, family = schema.order
    model = schema.model_at(family, 1)
    (slot,) = model.slots

    assert schema.target(model, slot.type) is schema.models(enum)[0]


def test_a_parent_whose_enum_gains_a_member_with_stable_numbers_is_one_model(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = value(2, since=3)\n\nclass P:\n    e: E\n"
    schema = Schema(build_package({"a": source}))
    _, family = schema.order

    assert len(schema.models(family)) == 1


def test_a_models_nested_holds_the_model_of_its_nested_enum(build_package):
    source = HEADER + (
        "class A:\n    class F(IntEnum, uint8):\n        X = value(1, until=3)\n        X = value(2, since=3)\n"
        "        Y = value(1, since=3)\n    f: F\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, family = schema.order

    assert schema.model_at(family, 1).nested == (schema.models(enum)[0],)


def test_a_nested_enum_model_is_owned_by_the_newest_model_that_holds_it(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n    f: F\n\n"
        + "@type(since=3)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n    f: F\n    y: uint8\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, family = schema.order

    assert schema.owner(schema.enum_type(enum, 1)) is schema.models(family)[1]


def test_a_top_level_model_has_no_owner(build_package):
    schema = Schema(build_package({"a": HEADER + "class A:\n    x: uint8\n"}))
    (family,) = schema.order

    assert schema.owner(schema.model_at(family, 1)) is None


def test_a_literal_whose_enum_gains_a_member_but_whose_number_does_not_keeps_one_encoding(build_package):
    source = (
        HEADER + "class E(IntEnum, uint8):\n    X = 1\n    Y = value(2, since=3)\n\nclass P:\n    tag: Literal[E.X]\n"
    )
    schema = Schema(build_package({"a": source}))
    _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 1


GROWING = HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = value(2, since=3)\n"

NESTED_ENUM_PAIR = (
    HEADER
    + "class A:\n    class F(IntEnum, uint8):\n        X = 1\n    f: F\n\n"
    + "@type(cereal=False)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n    f: F\n\n"
    + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False)\n"
)

SPLIT_NESTED_ENUM_PAIR = (
    HEADER
    + "@type(until=3)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n    f: F\n\n"
    + "@type(cereal=False, since=3, until=5)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n    f: F\n\n"
    + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False, since=3, until=5)\n"
)


@pytest.mark.parametrize("version", [1, 3, 5])
def test_enum_type_is_the_family_model_at_every_version_when_no_number_moves(build_package, version):
    schema = Schema(build_package({"a": GROWING}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert schema.enum_type(family, version) is model


def test_enum_types_of_an_unrenumbered_family_is_its_model(build_package):
    schema = Schema(build_package({"a": GROWING}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert schema.enum_types(family) == [model]


def test_enum_types_of_a_renumbered_family_is_its_model(build_package):
    schema = Schema(build_package({"a": RENUMBERED}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert schema.enum_types(family) == [model]


def test_enum_types_gives_both_forms_of_a_nested_pair_the_same_type(build_package):
    schema = Schema(build_package({"a": NESTED_ENUM_PAIR}))
    cereal, _, pre_cereal, _, _ = schema.order

    assert schema.enum_types(pre_cereal) == schema.enum_types(cereal)


def test_enumerators_of_a_model_are_its_library_values(build_package):
    schema = Schema(build_package({"a": DISPLACED}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert schema.enumerators(model) == {"A": 2, "B": 3}


def test_enum_runs_of_a_model_are_the_union_of_its_runs_over_both_forms(build_package):
    schema = Schema(build_package({"a": SPLIT_NESTED_ENUM_PAIR}))
    cereal, _, _, _, _ = schema.order
    (model,) = schema.models(cereal)

    assert schema.enum_runs(model) == [Range(None, 5)]


def test_two_struct_versions_differing_only_in_an_enum_that_gains_a_member_have_two_encodings(build_package):
    schema = Schema(build_package({"a": GROWING + "\nclass P:\n    e: E\n"}))
    _, family = schema.order
    (model,) = schema.models(family)

    assert len(schema.encodings(model)) == 2


@pytest.mark.parametrize(
    ("members", "order"),
    [
        pytest.param("    A = value(5, until=3)\n    B = value(5, since=3)\n", ["B", "A"], id="never live together"),
        pytest.param(
            "    A = value(5, until=5)\n    B = value(5, since=2, synonym=True)\n", ["B", "A"], id="live together"
        ),
        pytest.param(
            "    A = value(5, until=3)\n    B = value(5, since=2, until=4, synonym=True)\n    C = value(5, since=4)\n",
            ["C", "B", "A"],
            id="one pair live together",
        ),
    ],
)
def test_members_sharing_a_value_list_the_one_live_at_the_newest_version_first(build_package, members, order):
    schema = Schema(build_package({"a": HEADER + "class E(IntEnum, uint8):\n" + members}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert [member.name for member in model.members] == order


def test_members_sharing_a_value_live_at_the_same_newest_version_keep_their_declaration_order(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    A = 5\n    B = value(5, since=2, synonym=True)\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert [member.name for member in model.members] == ["A", "B"]


def test_members_sharing_a_value_are_reordered_only_within_the_positions_they_hold(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    A = value(5, until=3)\n    C = 7\n    B = value(5, since=3)\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert [member.name for member in model.members] == ["B", "C", "A"]


def test_members_sharing_a_value_are_ordered_by_the_versions_either_form_holds_them(build_package):
    source = (
        HEADER
        + "class A:\n    class F(IntEnum, uint8):\n        X = value(5, until=3)\n        Y = value(5, since=3)\n"
        + "    f: F\n\n"
        + "@type(cereal=False)\nclass A:\n    class F(IntEnum, uint8):\n        X = 5\n    f: F\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, _, _, _, _ = schema.order
    (model,) = schema.models(enum)

    assert [member.name for member in model.members] == ["X", "Y"]


def test_scope_of_an_enum_model_is_the_first_version_it_is_live(build_package):
    source = HEADER + "@type(since=2, until=4)\nclass E(IntEnum, uint8):\n    A = 1\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order
    (model,) = schema.models(family)

    assert schema.scope(model) == 2


def test_target_of_an_enum_slot_is_the_model_of_an_unrenumbered_family(build_package):
    schema = Schema(build_package({"a": GROWING + "\nclass P:\n    e: E\n"}))
    enum, family = schema.order
    model = schema.model_at(family, 1)
    (slot,) = model.slots

    assert schema.target(model, slot.type) is schema.models(enum)[0]


def test_a_temporary_owner_holding_an_enum_model_live_outside_the_overlap_is_rejected(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n    f: F\n\n"
        + "@type(since=3, until=5)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n    f: F\n    y: uint8\n\n"
        + "@type(cereal=False, since=3, until=5)\nclass A:\n    z: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False, since=3, until=5)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(
        CompilerError, match=r"a\.py: A\.F: is owned by CerealizedA but is live at 1, outside its overlap"
    ):
        Schema(package)


def test_a_shared_models_family_is_the_cereal_form(build_package):
    source = (
        HEADER
        + "@type(cereal=False)\nclass B:\n    x: uint16\n\nclass B:\n    x: uint16\n\n"
        + "@packet(id=1)\nclass A:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    pre_cereal, cereal, _ = schema.order

    assert [model.family for model in schema.models(pre_cereal)] == [cereal]


def test_a_shared_models_runs_hold_both_forms(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint16\n\n@type(cereal=False)\nclass B:\n    x: uint16\n\n"
        + "@packet(id=1)\nclass A:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, pre_cereal, _ = schema.order

    assert list(schema.model_at(cereal, 1).runs) == [cereal, pre_cereal]


def test_a_pre_cereal_model_no_cereal_model_equals_belongs_to_the_pre_cereal_form(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    x: uint16\n\n"
        + "@packet(id=1)\nclass A:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    _, pre_cereal, _ = schema.order

    assert [model.family for model in schema.models(pre_cereal)] == [pre_cereal]


ALL = Range(None, None)

OVERLAPPED = (
    HEADER
    + "@type(until=3)\nclass B:\n    x: uint8\n\n@type(since=3)\nclass B:\n    x: uint16\n\n"
    + "@type(cereal=False, until=4)\nclass B:\n    x: int32\n\n"
    + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False, until=4)\n"
)


def test_mixed_is_the_versions_where_both_forms_are_live(build_package):
    schema = Schema(build_package({"a": OVERLAPPED}))
    cereal, _, _ = schema.order

    assert schema.mixed(cereal) == [Range(None, 4)]


def test_the_overlap_is_the_mixed_versions_where_the_forms_hold_different_models(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass B:\n    x: uint8\n\n@type(since=3)\nclass B:\n    x: uint16\n\n"
        + "@type(cereal=False)\nclass B:\n    x: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, _ = schema.order

    assert (schema.mixed(cereal), schema.overlap(cereal)) == ([ALL], [Range(3, None)])


def test_the_overlap_of_forms_that_differ_at_every_mixed_version_is_the_mixed_versions(build_package):
    schema = Schema(build_package({"a": OVERLAPPED}))
    cereal, _, _ = schema.order

    assert schema.overlap(cereal) == [Range(None, 4)]


def test_a_pair_sharing_one_model_at_every_mixed_version_has_no_overlap(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint8\n\n@type(cereal=False, until=4)\nclass B:\n    x: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False, until=4)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, _ = schema.order

    assert (schema.mixed(cereal), schema.overlap(cereal)) == ([Range(None, 4)], [])


def test_mixed_is_bounded_by_both_forms(build_package):
    source = (
        HEADER
        + "@type(until=4)\nclass B:\n    x: uint8\n\n@type(cereal=False, since=2)\nclass B:\n    x: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False, since=2)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, _ = schema.order

    assert schema.mixed(cereal) == [Range(2, 4)]


def test_a_family_with_one_form_is_never_mixed(build_package):
    schema = Schema(build_package({"a": HEADER + "class A:\n    x: uint8\n"}))
    (family,) = schema.order

    assert schema.mixed(family) == []


def test_a_family_with_one_form_has_no_overlap(build_package):
    schema = Schema(build_package({"a": HEADER + "class A:\n    x: uint8\n"}))
    (family,) = schema.order

    assert schema.overlap(family) == []


@pytest.mark.parametrize(
    ("version", "label"),
    [
        pytest.param(1, "CerealizedB", id="first version"),
        pytest.param(3, "CerealizedB", id="last version of the overlap"),
        pytest.param(4, "B", id="first version past the overlap"),
        pytest.param(5, "B", id="last version"),
    ],
)
def test_the_label_of_a_cereal_family_is_prefixed_only_inside_the_overlap(build_package, version, label):
    schema = Schema(build_package({"a": OVERLAPPED}))
    cereal, _, _ = schema.order

    assert schema.label(cereal, version) == label


def test_the_label_of_a_hand_written_family_is_never_prefixed(build_package):
    schema = Schema(build_package({"a": OVERLAPPED}))
    _, pre_cereal, _ = schema.order

    assert schema.label(pre_cereal, 1) == "B"


def test_the_label_of_a_family_with_one_form_is_never_prefixed(build_package):
    schema = Schema(build_package({"a": HEADER + "class A:\n    x: uint8\n"}))
    (family,) = schema.order

    assert schema.label(family, 1) == "A"


def test_a_cereal_model_that_lives_only_inside_the_overlap_is_prefixed(build_package):
    schema = Schema(build_package({"a": OVERLAPPED}))
    cereal, _, _ = schema.order

    assert schema.name(schema.model_at(cereal, 1)) == "CerealizedB"


def test_a_cereal_model_that_lives_past_the_overlap_is_named_plain(build_package):
    schema = Schema(build_package({"a": OVERLAPPED}))
    cereal, _, _ = schema.order

    assert schema.name(schema.model_at(cereal, 3)) == "B"


def test_a_hand_written_model_living_only_inside_the_overlap_is_never_named_cerealized(build_package):
    schema = Schema(build_package({"a": OVERLAPPED}))
    _, pre_cereal, _ = schema.order

    assert schema.name(schema.model_at(pre_cereal, 1)) == "B"


def test_a_pair_sharing_one_model_at_every_mixed_version_is_never_labelled_cerealized(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint8\n\n@type(cereal=False, until=4)\nclass B:\n    x: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False, until=4)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, _ = schema.order

    assert schema.label(cereal, 1) == "B"


DIVERGING = (
    HEADER
    + "@type(until=3)\nclass B:\n    x: uint8\n\n@type(since=3)\nclass B:\n    x: uint16\n\n"
    + "@type(cereal=False)\nclass B:\n    x: uint8\n\n"
    + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False)\n"
)


@pytest.mark.parametrize(
    ("version", "label"),
    [
        pytest.param(1, "B", id="first version"),
        pytest.param(2, "B", id="last version holding one model"),
        pytest.param(3, "CerealizedB", id="first version holding two models"),
        pytest.param(5, "CerealizedB", id="last version"),
    ],
)
def test_the_label_of_a_pair_differing_at_some_versions_is_prefixed_exactly_there(build_package, version, label):
    schema = Schema(build_package({"a": DIVERGING}))
    cereal, _, _ = schema.order

    assert schema.label(cereal, version) == label


def test_a_cereal_model_held_by_the_hand_written_form_is_named_plain(build_package):
    schema = Schema(build_package({"a": DIVERGING}))
    cereal, _, _ = schema.order

    assert schema.name(schema.model_at(cereal, 1)) == "B"


def test_a_nested_model_keeps_its_own_name(build_package):
    source = (
        HEADER
        + "class A:\n    class Inner:\n        x: uint8\n    i: Inner\n\n"
        + "@type(cereal=False)\nclass A:\n    class Inner:\n        x: uint16\n    i: Inner\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    inner, _, _, _, _ = schema.order

    assert schema.name(schema.model_at(inner, 1)) == "Inner"


def test_a_bare_cereal_model_may_share_a_name_with_a_hand_written_model_under_a_version(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint8\n\n@type(cereal=False, until=3)\nclass B:\n    x: uint16\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False, until=3)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, pre_cereal, _ = schema.order

    assert (schema.name(schema.model_at(cereal, 1)), schema.name(schema.model_at(pre_cereal, 1))) == ("B", "B")


def test_a_nested_child_living_past_the_overlap_is_owned_by_a_plain_named_model(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n    f: F\n\n"
        + "@type(since=3)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n    f: F\n    y: uint8\n\n"
        + "@type(cereal=False, until=3)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n    f: F\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False, until=3)\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, _, _, _, _ = schema.order

    assert schema.name(schema.owner(schema.enum_type(enum, 1))) == "A"


def test_a_hand_written_form_no_packet_reaches_is_rejected(build_package):
    source = HEADER + "class B:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    x: uint8\n"
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"a\.py: B: the hand-written form is live at 1 but no packet reaches it"):
        Schema(package)


def test_a_hand_written_form_reached_only_by_a_struct_that_is_not_a_packet_is_rejected(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    x: uint8\n\n"
        + "class A:\n    b: B = field(cereal=False)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"a\.py: B: the hand-written form is live at 1 but no packet reaches it"):
        Schema(package)


def test_a_hand_written_form_names_the_first_version_no_packet_reaches_it_at(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    x: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False, until=3)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(CompilerError, match=r"a\.py: B: the hand-written form is live at 3 but no packet reaches it"):
        Schema(package)


def test_two_models_of_a_pair_with_one_name_and_scope_are_rejected(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass B:\n    x: uint8\n\n@type(since=3)\nclass B:\n    x: uint16\n\n"
        + "@type(cereal=False, until=2)\nclass B:\n    x: int32\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False, until=2)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(
        CompilerError, match=r"a\.py: B: the hand-written and the cereal form both hold a type named B from 1"
    ):
        Schema(package)


def test_two_bare_models_of_a_pair_with_one_name_are_rejected(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint8\n\n@type(cereal=False, since=3)\nclass B:\n    x: uint16\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False, since=3)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(
        CompilerError, match=r"a\.py: B: the hand-written and the cereal form both hold a type named B at 5$"
    ):
        Schema(package)


def test_a_reached_pre_cereal_form_holding_an_unreferenced_nested_enum_is_accepted(build_package):
    source = (
        HEADER
        + "class B:\n    class F(IntEnum, uint8):\n        X = 1\n    x: uint8\n\n"
        + "@type(cereal=False)\nclass B:\n    class F(IntEnum, uint8):\n        X = 1\n    x: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    _, _, _, pre_cereal, _ = schema.order

    assert len(schema.model_at(pre_cereal, 1).nested) == 1


def test_a_nested_child_living_only_inside_the_overlap_is_owned_by_a_cerealized_model(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n        Y = 2\n    f: F\n\n"
        + "@type(cereal=False, until=3)\nclass A:\n    x: uint16\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False, until=3)\n"
    )
    schema = Schema(build_package({"a": source}))
    enum, _, _, _ = schema.order

    assert schema.name(schema.owner(schema.models(enum)[0])) == "CerealizedA"


def test_a_bare_cereal_model_may_share_a_name_and_since_with_a_hand_written_model_under_a_version(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass B:\n    x: uint8\n\n@type(since=3)\nclass B:\n    x: uint16\n\n"
        + "@type(cereal=False, since=3, until=5)\nclass B:\n    x: int32\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False, since=3, until=5)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, pre_cereal, _ = schema.order

    assert (schema.name(schema.model_at(cereal, 3)), schema.name(schema.model_at(pre_cereal, 3))) == ("B", "B")


def test_a_nested_child_is_owned_by_the_holder_that_returns_at_the_latest_version(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    class B:\n        x: uint8\n    b: B\n\n"
        + "@type(since=3, until=4)\nclass A:\n    class B:\n        x: uint8\n    b: B\n    y: uint8\n\n"
        + "@type(since=4)\nclass A:\n    class B:\n        x: uint8\n    b: B\n"
    )
    schema = Schema(build_package({"a": source}))
    nested, owner = schema.order
    (inner,) = schema.models(nested)

    assert schema.owner(inner) is schema.model_at(owner, 5)


def test_a_temporary_owner_holding_a_child_live_outside_the_overlap_is_rejected(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n        Y = 2\n    f: F\n\n"
        + "@type(since=3, until=5)\nclass A:\n    class F(IntEnum, uint8):\n        X = 1\n        Y = 2\n"
        + "    f: F\n    y: uint8\n\n"
        + "@type(cereal=False, since=3, until=5)\nclass A:\n    x: uint16\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False, since=3, until=5)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(
        CompilerError, match=r"a\.py: A\.F: is owned by CerealizedA but is live at 1, outside its overlap"
    ):
        Schema(package)


def test_a_model_live_at_the_latest_version_has_no_scope(build_package):
    source = HEADER + "@type(until=3)\nclass A:\n    x: uint8\n\n@type(since=3)\nclass A:\n    x: uint16\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert schema.scope(schema.model_at(family, 5)) is None


def test_an_older_models_scope_is_its_first_version(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    x: uint8\n\n@type(since=3, until=4)\nclass A:\n    x: uint16\n\n"
        + "@type(since=4)\nclass A:\n    x: int8\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert schema.scope(schema.model_at(family, 3)) == 3


def test_the_oldest_models_scope_is_the_first_modelled_version(build_package):
    source = HEADER + "@type(until=3)\nclass A:\n    x: uint8\n\n@type(since=3)\nclass A:\n    x: uint16\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert schema.scope(schema.model_at(family, 1)) == 1


def test_a_family_that_ends_before_the_latest_version_has_no_bare_model(build_package):
    schema = Schema(build_package({"a": HEADER + "@type(until=4)\nclass A:\n    x: uint8\n"}))
    (family,) = schema.order

    assert schema.scope(schema.model_at(family, 1)) == 1


def test_an_enum_model_live_at_the_latest_version_has_no_scope(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = value(2, since=3)\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert schema.scope(schema.enum_type(family, 5)) is None


def test_an_enum_that_ends_before_the_latest_version_has_no_bare_model(build_package):
    source = HEADER + "@type(until=4)\nclass E(IntEnum, uint8):\n    A = 1\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert schema.scope(schema.enum_type(family, 1)) == 1


def test_a_cereal_model_starting_before_the_overlap_is_named_plain(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass B:\n    x: uint8\n\n@type(since=3)\nclass B:\n    x: uint16\n\n"
        + "@type(cereal=False, since=2)\nclass B:\n    x: uint16\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False, since=2)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, _ = schema.order

    assert schema.name(schema.model_at(cereal, 1)) == "B"


def test_a_nested_child_of_both_forms_may_share_a_name_and_scope(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass A:\n    class Inner:\n        x: uint8\n    i: Inner\n\n"
        + "@type(cereal=False, until=3)\nclass A:\n    class Inner:\n        x: uint16\n    i: Inner\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False, until=3)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, pre_cereal, _, _ = schema.order

    assert (schema.name(schema.model_at(cereal, 1)), schema.name(schema.model_at(pre_cereal, 1))) == ("Inner", "Inner")


def test_a_hand_written_enum_declared_at_module_scope_is_rejected(build_package):
    source = (
        HEADER + "class E(IntEnum, uint8):\n    A = 1\n\n@type(cereal=False)\nclass E(IntEnum, uint8):\n    A = 1\n"
    )
    package = build_package({"a": source})

    with pytest.raises(
        CompilerError,
        match=r"a\.py: E: a cereal=False enum is declared at module scope",
    ):
        Schema(package)


def test_the_label_of_a_nested_cereal_family_is_never_prefixed(build_package):
    source = (
        HEADER
        + "class A:\n    class Inner:\n        x: uint8\n    i: Inner\n\n"
        + "@type(cereal=False)\nclass A:\n    class Inner:\n        x: uint16\n    i: Inner\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    inner, _, _, _, _ = schema.order

    assert schema.label(inner, 1) == "Inner"


def test_the_scope_of_a_nested_model_is_rejected(build_package):
    source = HEADER + "class A:\n    class Inner:\n        x: uint8\n    i: Inner\n"
    schema = Schema(build_package({"a": source}))
    inner, _ = schema.order

    with pytest.raises(CompilerError, match=r"a\.py: A\.Inner: is nested and is named through its owner"):
        schema.scope(schema.model_at(inner, 1))


def test_an_enum_shape_that_returns_at_the_latest_version_has_no_scope(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = value(2, since=3, until=4)\n"
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert schema.scope(schema.enum_type(family, 1)) is None


TIED = (
    HEADER
    + "class B:\n    x: uint8\n\n@type(cereal=False, until=4)\nclass B:\n    x: uint8\n\n"
    + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False, until=4)\n"
)

SPLIT = (
    HEADER
    + "class B:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    x: uint16\n\n"
    + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False)\n"
)


def test_an_encoding_of_a_class_with_one_mode_is_keyed_default(build_package):
    schema = Schema(build_package({"a": HEADER + "class A:\n    x: uint8\n"}))
    (family,) = schema.order

    assert schema.encoding_at(family, 1).mode is SerializationMode.DEFAULT


def test_an_encoding_only_the_cereal_form_uses_while_the_pair_is_mixed_is_keyed_cereal(build_package):
    schema = Schema(build_package({"a": SPLIT}))
    cereal, _, _ = schema.order

    assert schema.encoding_at(cereal, 1).mode is SerializationMode.CEREAL


def test_an_encoding_only_the_hand_written_form_uses_while_the_pair_is_mixed_is_keyed_manual(build_package):
    schema = Schema(build_package({"a": SPLIT}))
    _, pre_cereal, _ = schema.order

    assert schema.encoding_at(pre_cereal, 1).mode is SerializationMode.MANUAL


def test_an_encoding_both_forms_use_at_its_first_version_is_keyed_cereal(build_package):
    schema = Schema(build_package({"a": TIED}))
    cereal, pre_cereal, _ = schema.order

    assert (
        schema.encoding_at(pre_cereal, 1) is schema.encoding_at(cereal, 1),
        schema.encoding_at(cereal, 1).mode,
    ) == (
        True,
        SerializationMode.CEREAL,
    )


def test_served_lists_the_runs_of_an_encoding_per_mode(build_package):
    schema = Schema(build_package({"a": TIED}))
    cereal, _, _ = schema.order

    assert schema.encoding_at(cereal, 1).served == {
        SerializationMode.CEREAL: [Range(None, 4)],
        SerializationMode.MANUAL: [Range(None, 4)],
        SerializationMode.DEFAULT: [Range(4, None)],
    }


CALLS = (
    HEADER
    + "class B:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    x: uint16\n\n"
    + "@packet(id=1)\nclass Hand:\n    b: B = field(cereal=False)\n\n"
    + "@packet(id=2)\nclass Plain:\n    b: B\n\n"
    + "class C:\n    x: uint8\n\n@packet(id=3)\nclass Single:\n    c: C\n"
)


def test_a_call_through_a_cereal_false_field_names_the_manual_mode(build_package):
    schema = Schema(build_package({"a": CALLS}))
    _, pre_cereal, hand, _, _, _ = schema.order

    assert schema.call(schema.encoding_at(hand, 1), StructRef(pre_cereal)) == (1, SerializationMode.MANUAL)


def test_a_call_through_a_plain_field_of_a_cereal_parent_names_the_cereal_mode(build_package):
    schema = Schema(build_package({"a": CALLS}))
    cereal, _, _, plain, _, _ = schema.order

    assert schema.call(schema.encoding_at(plain, 1), StructRef(cereal)) == (1, SerializationMode.CEREAL)


def test_a_call_to_a_class_with_one_mode_names_the_default_mode(build_package):
    schema = Schema(build_package({"a": CALLS}))
    _, _, _, _, child, single = schema.order

    assert schema.call(schema.encoding_at(single, 1), StructRef(child)) == (1, SerializationMode.DEFAULT)


def test_a_child_born_mixed_is_called_by_its_key_mode_from_a_later_version(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint8\n\n"
        + "@type(cereal=False, until=3)\nclass B:\n    x: uint16\n\n"
        + "@type(cereal=False, since=3)\nclass B:\n    x: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    _, pre_cereal, family = schema.order

    assert schema.call(schema.encoding_at(family, 3), StructRef(pre_cereal)) == (1, SerializationMode.CEREAL)


def test_the_scope_of_a_shared_model_is_bare_when_the_hand_written_form_holds_it_at_the_latest_version(build_package):
    source = (
        HEADER
        + "@type(until=4)\nclass B:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    x: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, _ = schema.order

    assert schema.scope(schema.model_at(cereal, 1)) is None


def test_the_scope_of_a_shared_model_is_bare_when_the_cereal_form_holds_it_at_the_latest_version(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint8\n\n@type(cereal=False, until=4)\nclass B:\n    x: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False, until=4)\n"
    )
    schema = Schema(build_package({"a": source}))
    _, pre_cereal, _ = schema.order

    assert schema.scope(schema.model_at(pre_cereal, 1)) is None


def test_the_scope_of_a_shared_model_no_form_holds_at_the_latest_version_is_its_first_version(build_package):
    source = (
        HEADER
        + "@type(since=3, until=5)\nclass B:\n    x: uint8\n\n"
        + "@type(cereal=False, since=2, until=4)\nclass B:\n    x: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False, since=2, until=4)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, _ = schema.order

    assert schema.scope(schema.model_at(cereal, 3)) == 2


def test_the_read_version_of_a_shared_model_is_its_newest_version_over_both_forms(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass B:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    x: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, _ = schema.order

    assert schema.read_at[schema.model_at(cereal, 1)] == 5


def test_a_nested_child_of_a_shared_model_is_owned_by_that_model(build_package):
    source = (
        HEADER
        + "class A:\n    class Inner:\n        x: uint8\n    i: Inner\n\n"
        + "@type(cereal=False)\nclass A:\n    class Inner:\n        x: uint8\n    i: Inner\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    inner, family, _, _, _ = schema.order

    assert schema.owner(schema.model_at(inner, 1)) is schema.model_at(family, 1)


def test_the_scope_of_an_enum_shape_with_two_runs_takes_its_first_version_from_the_first_run(build_package):
    source = HEADER + (
        "@type(until=6)\nclass E(IntEnum, uint8):\n    A = value(1, until=3)\n    A = value(2, since=3, until=4)\n"
        "    A = value(1, since=4)\n"
    )
    schema = Schema(build_package({"a": source}, APPENDED_INIT))
    (family,) = schema.order

    assert schema.scope(schema.enum_type(family, 1)) == 1


def test_target_accepts_an_enum_read_by_name(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    X = 1\n\nclass P:\n    e: E = field(type=str)\n"
    schema = Schema(build_package({"a": source}))
    enum, family = schema.order

    assert schema.target(schema.model_at(family, 1), EnumName(enum)) is schema.models(enum)[0]


def test_a_call_through_a_cereal_false_field_names_the_manual_mode_of_a_shared_encoding(build_package):
    schema = Schema(build_package({"a": TIED}))
    _, pre_cereal, family = schema.order

    assert schema.call(schema.encoding_at(family, 1), StructRef(pre_cereal)) == (1, SerializationMode.MANUAL)


SHARED_UNDER_HAND = (
    HEADER
    + "class B:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    x: {manual}\n\n"
    + "class A:\n    y: uint8\n    b: B\n\n@type(cereal=False)\nclass A:\n    b: B\n\n"
    + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False)\n\n"
    + "@packet(id=2)\nclass Q:\n    b: B = field(cereal=False)\n"
)


def test_a_call_from_a_hand_written_parent_through_a_plain_field_names_the_manual_mode(build_package):
    schema = Schema(build_package({"a": SHARED_UNDER_HAND.format(manual="uint8")}))
    cereal, _, _, hand, _, _ = schema.order

    assert schema.call(schema.encoding_at(hand, 1), StructRef(cereal)) == (1, SerializationMode.MANUAL)


def test_a_call_from_a_hand_written_parent_falls_back_to_the_key_mode_of_a_child_without_a_manual_mode(build_package):
    schema = Schema(build_package({"a": SHARED_UNDER_HAND.format(manual="uint16")}))
    cereal, _, _, hand, _, _ = schema.order

    assert schema.call(schema.encoding_at(hand, 1), StructRef(cereal)) == (1, SerializationMode.CEREAL)


def test_mixed_of_a_nested_struct_is_the_mixed_versions_of_its_outermost_pair(build_package):
    source = (
        HEADER
        + "class A:\n    @type(since=2)\n    class Inner:\n        x: uint8\n\n"
        + "    i: Inner = field(since=2)\n    y: uint8\n\n"
        + "@type(cereal=False, until=4)\nclass A:\n    class Inner:\n        x: uint8\n    i: Inner\n    y: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False, until=4)\n"
    )
    schema = Schema(build_package({"a": source}))
    inner, _, _, _, _ = schema.order

    assert schema.mixed(inner) == [Range(None, 4)]


def test_a_shared_model_whose_cereal_life_lies_inside_the_overlap_is_never_named_cerealized(build_package):
    source = (
        HEADER
        + "@type(until=2)\nclass B:\n    x: uint16\n\n"
        + "@type(since=2, until=3)\nclass B:\n    x: uint8\n\n"
        + "@type(since=3, until=5)\nclass B:\n    x: uint16\n\n"
        + "@type(cereal=False, until=3)\nclass B:\n    x: uint16\n\n"
        + "@type(cereal=False, since=3, until=4)\nclass B:\n    x: uint8\n\n"
        + "@type(cereal=False, since=4, until=5)\nclass B:\n    x: uint16\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False, until=5)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, _ = schema.order

    assert schema.name(schema.model_at(cereal, 2)) == "B"


def test_a_nested_child_held_at_the_same_newest_version_by_a_temporary_and_a_plain_owner_is_owned_by_the_plain_one(
    build_package,
):
    source = (
        HEADER
        + "@type(since=3, until=5)\nclass A:\n    class N:\n        x: uint8\n    n: N\n    y: uint8\n\n"
        + "@type(cereal=False, until=5)\nclass A:\n    class N:\n        x: uint8\n    n: N\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False, until=5)\n"
    )
    schema = Schema(build_package({"a": source}))
    inner, _, _, pre_cereal, _ = schema.order

    assert schema.owner(schema.model_at(inner, 3)) is schema.model_at(pre_cereal, 3)


def test_a_model_both_forms_hold_at_every_version_is_not_versioned_although_its_cereal_form_starts_later(
    build_package,
):
    source = (
        HEADER
        + "@type(since=3)\nclass B:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    x: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, _ = schema.order

    assert schema.model_at(cereal, 3).versioned is False


def test_a_call_from_a_parent_both_forms_share_names_the_cereal_mode(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    x: uint8\n\n"
        + "class A:\n    b: B\n\n@type(cereal=False)\nclass A:\n    b: B\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False)\n\n"
        + "@packet(id=2)\nclass Q:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, parent, _, _, _ = schema.order

    assert schema.call(schema.encoding_at(parent, 1), StructRef(cereal)) == (1, SerializationMode.CEREAL)


def test_a_temporary_owner_holding_a_child_live_inside_mixed_but_outside_the_overlap_is_rejected(build_package):
    source = (
        HEADER
        + "@type(until=2)\nclass A:\n    class N:\n        x: uint8\n    n: N\n\n"
        + "@type(since=2, until=4)\nclass A:\n    class N:\n        x: uint8\n    n: N\n    y: uint8\n\n"
        + "@type(cereal=False, until=2)\nclass A:\n    class N:\n        x: uint8\n    n: N\n\n"
        + "@type(cereal=False, since=2, until=4)\nclass A:\n    z: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False, until=4)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(
        CompilerError, match=r"a\.py: A\.N: is owned by CerealizedA but is live at 1, outside its overlap"
    ):
        Schema(package)


def test_the_slots_of_a_shared_model_come_from_the_cereal_form_when_both_hold_it_at_its_newest_version(build_package):
    source = (
        HEADER
        + "class B:\n    x: uint8\n    y: uint16\n\n@type(cereal=False)\nclass B:\n    y: uint16\n    x: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    b: B = field(cereal=False)\n"
    )
    schema = Schema(build_package({"a": source}))
    cereal, _, _ = schema.order

    assert [slot.name for slot in schema.model_at(cereal, 1).slots] == ["x", "y"]


def test_a_nested_child_held_at_the_same_newest_version_by_two_plain_owners_is_owned_by_the_cereal_one(build_package):
    source = (
        HEADER
        + "@type(until=5)\nclass A:\n    class N:\n        x: uint8\n    n: N\n    y: uint8\n\n"
        + "@type(cereal=False, since=3, until=5)\nclass A:\n    class N:\n        x: uint8\n    n: N\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False, since=3, until=5)\n"
    )
    schema = Schema(build_package({"a": source}))
    inner, cereal, _, _, _ = schema.order

    assert schema.owner(schema.model_at(inner, 3)) is schema.model_at(cereal, 3)


def test_a_temporary_owner_holding_a_child_only_the_hand_written_form_holds_outside_the_overlap_is_rejected(
    build_package,
):
    source = (
        HEADER
        + "@type(since=2, until=4)\nclass A:\n    class N:\n        x: uint8\n    n: N\n    y: uint8\n\n"
        + "@type(cereal=False, until=2)\nclass A:\n    class N:\n        x: uint8\n    n: N\n\n"
        + "@type(cereal=False, since=2, until=4)\nclass A:\n    z: uint8\n\n"
        + "@packet(id=1)\nclass P:\n    a: A = field(cereal=False, until=4)\n"
    )
    package = build_package({"a": source})

    with pytest.raises(
        CompilerError, match=r"a\.py: A\.N: is owned by CerealizedA but is live at 1, outside its overlap"
    ):
        Schema(package)


def test_every_serializer_numbers_an_enum_as_numbering_of_selects_at_each_protocol_it_serves():
    schema = Schema(build(ROOT / "protocol"))
    selected = {
        (numbering.model, version): numbering
        for numberings in schema.model_numberings.values()
        for numbering in numberings
        if not numbering.identity
        for run in numbering.runs
        for version in schema.versions
        if run.contains(version)
    }
    served = [
        (encoding, numbering, version)
        for encodings in schema.model_encodings.values()
        for encoding in encodings
        for numbering in encoding.reached.values()
        if isinstance(numbering, Numbering)
        for runs in encoding.served.values()
        for run in runs
        for version in schema.versions
        if run.contains(version)
    ]

    assert served
    assert [
        (encoding.model.family.name, numbering.model.family.name, version)
        for encoding, numbering, version in served
        if selected.get((numbering.model, version)) is not (None if numbering.identity else numbering)
    ] == []
