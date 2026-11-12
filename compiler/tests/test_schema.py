from bedrock_protocol_compiler.descriptor import Binary, Int, MemberRef, Range
from bedrock_protocol_compiler.schema import Schema, roots_reached

HEADER = """
from enum import IntEnum, auto
from protocol import field, packet, sentinel, type, uint8, uint16, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"
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

MODELLED_INIT = """
from bedrock_protocol_compiler.dsl import field, int64, packet, type, uint8, uint16, value

versions = (729, 748, 766, 776, 786, 800, 818, 819, 827, 844, 859, 898, 924, 944, 975, 1001, 2168, 2193, 2225)

releases = {
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
        + "class A:\n    b: B = field(cereal=False)\n"
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

    assert (schema.versions, schema.latest) == ((1, 2, 3, 4, 5), 5)


def test_enum_values_are_evaluated_over_the_members_present(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 4\n    B = value(5, since=3)\n    C = auto()\n    D = A\n    F = C - 1\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    early, late = schema.shapes(family)

    assert [(member.name, member.value) for member in early.members] == [
        ("A", Int(4)),
        ("C", Int(5)),
        ("D", MemberRef(family, "A")),
        ("F", Binary("-", MemberRef(family, "C"), Int(1))),
    ]
    assert late.numbers == {"A": 4, "B": 5, "C": 6, "D": 4, "F": 5}


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


def test_an_enum_whose_underlying_type_changes_is_a_new_shape(build_package):
    source = (
        HEADER
        + "@type(until=3)\nclass E(IntEnum, uint8):\n    A = 1\n\n"
        + "@type(since=3)\nclass E(IntEnum, uint16):\n    A = 1\n"
    )
    schema = Schema(build_package({"a": source}))
    (family,) = schema.order

    assert [shape.ranges for shape in schema.shapes(family)] == [[Range(None, 3)], [Range(3, None)]]


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
        + "class A:\n    a: uint8\n    b: uint8 = field(when=lambda p: p.a == E.X)\n\n"
        + "class E(IntEnum, uint8):\n    X = value(1, until=3)\n    X = value(2, since=3)\n"
    )
    schema = Schema(build_package({"a": source}))
    _, a = schema.order

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
