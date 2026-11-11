import pytest

from bedrock_protocol_compiler.descriptor import CompilerError, Range

HEADER = """
from enum import IntEnum, auto
from typing import Literal
from protocol import array, bitset, field, packet, type, uint8, value
package = "bedrock.protocol"
"""


def test_declarations_carry_their_ranges(build_package):
    package = build_package(
        {
            "a": HEADER
            + "@packet(id=1, until=3)\nclass A:\n    x: uint8 = field(since=2)\n\n"
            + "@packet(id=1, since=3)\nclass A:\n    y: uint8 = field(until=5)\n"
        }
    )

    (family,) = package.modules[0].families

    assert [declaration.range for declaration in family.declarations] == [Range(None, 3), Range(3, None)]


def test_fields_are_clipped_to_their_declaration(build_package):
    package = build_package(
        {
            "a": HEADER
            + "@packet(id=1, until=3)\nclass A:\n    x: uint8 = field(since=2)\n\n"
            + "@packet(id=1, since=3)\nclass A:\n    y: uint8 = field(until=5)\n"
        }
    )

    (family,) = package.modules[0].families

    assert [declaration.fields[0].range for declaration in family.declarations] == [Range(2, 3), Range(3, 5)]


def test_members_are_clipped_to_their_declaration(build_package):
    package = build_package(
        {"a": HEADER + "@type(until=4)\nclass E(IntEnum, uint8):\n    A = value(1, since=2)\n    B = 2\n"}
    )

    (family,) = package.modules[0].families

    assert [member.range for member in family.declarations[0].members] == [Range(2, 4), Range(None, 4)]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("@packet(id=1, since=9)\nclass A:\n    pass\n", "A: since 9 is not a modelled version"),
        ("@type(until=9)\nclass A:\n    pass\n", "A: until 9 is not a modelled version"),
        ("class A:\n    x: uint8 = field(since=9)\n", "x: since 9 is not a modelled version"),
        ("class E(IntEnum):\n    A = value(1, until=9)\n", "A: until 9 is not a modelled version"),
        ("@type(since=3, until=3)\nclass A:\n    pass\n", "A: has an empty version range"),
        ("class A:\n    x: uint8 = field(since=4, until=2)\n", "x: has an empty version range"),
        ("@type(since=2)\nclass A:\n    x: uint8 = field(since=2)\n", "x: has a gate its declaration already decides"),
        ("@type(since=2)\nclass A:\n    x: uint8 = field(since=1)\n", "x: has a gate its declaration already decides"),
        ("@type(until=3)\nclass A:\n    x: uint8 = field(until=3)\n", "x: has a gate its declaration already decides"),
        ("@type(until=3)\nclass A:\n    x: uint8 = field(since=3)\n", "x: has a gate its declaration already decides"),
        ("@type(since=3)\nclass A:\n    x: uint8 = field(until=3)\n", "x: has a gate its declaration already decides"),
        (
            "@type(until=3)\nclass E(IntEnum):\n    A = value(1, until=4)\n",
            "A: has a gate its declaration already decides",
        ),
    ],
)
def test_bad_gate_is_rejected(build_package, source, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + source})


def test_a_gate_that_cuts_the_declaration_is_accepted(build_package):
    package = build_package({"a": HEADER + "@type(since=2, until=5)\nclass A:\n    x: uint8 = field(since=3)\n"})

    assert package.modules[0].families[0].declarations[0].fields[0].range == Range(3, 5)


def test_redeclarations_are_one_family(build_package):
    package = build_package(
        {"a": HEADER + "@type(until=2)\nclass A:\n    x: uint8\n\n@type(since=2)\nclass A:\n    y: uint8\n"}
    )

    (family,) = package.modules[0].families

    assert [[field.name for field in declaration.fields] for declaration in family.declarations] == [["x"], ["y"]]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "@type(until=2)\nclass A:\n    pass\n\n@type(since=3)\nclass A:\n    pass\n",
            "A: starts at 3, but its previous declaration ends at 2",
        ),
        (
            "@type(until=3)\nclass A:\n    pass\n\n@type(since=2)\nclass A:\n    pass\n",
            "A: starts at 2, but its previous declaration ends at 3",
        ),
        (
            "@type(until=3)\nclass A:\n    pass\n\n@type(until=5)\nclass A:\n    pass\n",
            "A: starts at None, but its previous declaration ends at 3",
        ),
        (
            "@type(since=2)\nclass A:\n    pass\n\n@type(since=2)\nclass A:\n    pass\n",
            "A: is declared again after an open declaration",
        ),
        (
            "@type()\nclass A:\n    pass\n\n@type(since=2)\nclass A:\n    pass\n",
            "A: is declared again after an open declaration",
        ),
    ],
)
def test_redeclarations_must_tile(build_package, source, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + source})


def test_redeclared_enums_must_tile(build_package):
    source = (
        "@type(until=3)\nclass E(IntEnum, uint8):\n    A = 1\n\n@type(since=4)\nclass E(IntEnum, uint8):\n    A = 1\n"
    )

    with pytest.raises(CompilerError, match="E: starts at 4, but its previous declaration ends at 3"):
        build_package({"a": HEADER + source})


def test_a_packet_keeps_one_id(build_package):
    source = "@packet(id=1, until=3)\nclass A:\n    pass\n\n@packet(id=2, since=3)\nclass A:\n    pass\n"

    with pytest.raises(CompilerError, match="A: is declared with packet ids 1 and 2"):
        build_package({"a": HEADER + source})


def test_a_packet_and_a_type_do_not_share_a_name(build_package):
    source = "@packet(id=1, until=3)\nclass A:\n    pass\n\n@type(since=3)\nclass A:\n    pass\n"

    with pytest.raises(CompilerError, match="A: is declared with packet ids 1 and None"):
        build_package({"a": HEADER + source})


def test_a_struct_and_an_enum_do_not_share_a_name(build_package):
    source = "@type(until=3)\nclass A:\n    pass\n\n@type(since=3)\nclass A(IntEnum):\n    B = 1\n"

    with pytest.raises(CompilerError, match="A: is already declared"):
        build_package({"a": HEADER + source})


def test_two_packets_may_take_one_id_in_turn(build_package):
    package = build_package(
        {"a": HEADER + "@packet(id=1, until=3)\nclass A:\n    pass\n\n@packet(id=1, since=3)\nclass B:\n    pass\n"}
    )

    assert [family.name for family in package.modules[0].families] == ["A", "B"]


@pytest.mark.parametrize(
    "source",
    [
        "@packet(id=1, until=3)\nclass A:\n    pass\n\n@packet(id=1, since=2)\nclass B:\n    pass\n",
        "@packet(id=1)\nclass A:\n    pass\n\n@packet(id=1, since=2)\nclass B:\n    pass\n",
        "@packet(id=1, since=2)\nclass A:\n    pass\n\n@packet(id=1, since=1, until=4)\nclass B:\n    pass\n",
        "@packet(id=1)\nclass A:\n    pass\n\n@packet(id=1)\nclass B:\n    pass\n",
    ],
)
def test_two_packets_on_one_id_must_not_overlap(build_package, source):
    with pytest.raises(CompilerError, match="B: takes packet id 1 from A"):
        build_package({"a": HEADER + source})


def test_two_packets_on_one_id_across_modules_must_not_overlap(build_package):
    with pytest.raises(CompilerError, match="B: takes packet id 1 from A"):
        build_package(
            {"a": HEADER + "@packet(id=1)\nclass A:\n    pass\n", "b": HEADER + "@packet(id=1)\nclass B:\n    pass\n"}
        )


def test_a_name_shared_by_two_modules_is_rejected(build_package):
    with pytest.raises(CompilerError, match="A: is already declared in a"):
        build_package(
            {"a": HEADER + "@type(until=2)\nclass A:\n    pass\n", "b": HEADER + "@type(since=2)\nclass A:\n    pass\n"}
        )


def test_the_legacy_flavour_of_a_name_shared_by_two_modules_is_rejected(build_package):
    with pytest.raises(CompilerError, match="B: is already declared in a"):
        build_package(
            {
                "a": HEADER + "class B:\n    pass\n\n@type(cereal=False)\nclass B:\n    pass\n",
                "b": HEADER + "@type(cereal=False)\nclass B:\n    pass\n",
            }
        )


def test_a_union_alias_shares_the_module_scope_namespace(build_package):
    with pytest.raises(CompilerError, match="A: is already declared in a"):
        build_package({"a": HEADER + "class A:\n    pass\n", "b": HEADER + "type A = uint8 | None\n"})


def test_the_legacy_flavour_is_redeclared_beside_its_cereal_family(build_package):
    package = build_package(
        {
            "a": HEADER
            + "class A:\n    pass\n\n"
            + "@type(cereal=False, until=2)\nclass A:\n    pass\n\n"
            + "@type(cereal=False, since=2)\nclass A:\n    pass\n"
        }
    )

    legacy = package.modules[0].families[1]

    assert [declaration.range for declaration in legacy.declarations] == [Range(None, 2), Range(2, None)]


def test_nested_families_merge_across_owner_redeclarations(build_package):
    package = build_package(
        {
            "a": HEADER
            + "@type(until=3)\nclass A:\n    class B:\n        x: uint8\n    b: B\n\n"
            + "@type(since=3)\nclass A:\n    class B:\n        y: uint8\n    b: B\n"
        }
    )

    (family,) = package.modules[0].families
    (nested,) = family.nested

    assert [declaration.range for declaration in nested.declarations] == [Range(None, 3), Range(3, None)]
    assert [declaration.fields[0].type.struct for declaration in family.declarations] == [nested, nested]


def test_a_nested_range_is_clipped_to_its_owner(build_package):
    source = "@type(since=2, until=5)\nclass A:\n    @type(until=4)\n    class B:\n        x: uint8 = field(since=3)\n"

    package = build_package({"a": HEADER + source})

    (nested,) = package.modules[0].families[0].nested

    assert nested.declarations[0].range == Range(2, 4)
    assert nested.declarations[0].fields[0].range == Range(3, 4)


def test_a_nested_range_outside_its_owner_is_rejected(build_package):
    source = "@type(until=3)\nclass A:\n    @type(since=4)\n    class B:\n        pass\n"

    with pytest.raises(CompilerError, match="B: is empty within its owner"):
        build_package({"a": HEADER + source})


def test_nested_redeclarations_must_tile(build_package):
    source = (
        "class A:\n    @type(until=2)\n    class B:\n        pass\n\n    @type(since=3)\n    class B:\n        pass\n"
    )

    with pytest.raises(CompilerError, match="B: starts at 3, but its previous declaration ends at 2"):
        build_package({"a": HEADER + source})


def test_a_nested_enum_redeclares_with_its_owner(build_package):
    package = build_package(
        {
            "a": HEADER
            + "@type(until=3)\nclass A:\n    class E(IntEnum, uint8):\n        X = 1\n\n"
            + "@type(since=3)\nclass A:\n    class E(IntEnum, uint8):\n        X = 2\n"
        }
    )

    (nested,) = package.modules[0].families[0].nested

    assert [declaration.range for declaration in nested.declarations] == [Range(None, 3), Range(3, None)]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "@type(since=3)\nclass B:\n    pass\n\nclass A:\n    x: B\n",
            "a.py: A.x: reaches B, which does not exist at 1",
        ),
        (
            "@type(until=3)\nclass B:\n    pass\n\nclass A:\n    x: B | None\n",
            "a.py: A.x: reaches B, which does not exist at 3",
        ),
        (
            "@type(until=3)\nclass B:\n    pass\n\nclass A:\n    x: list[dict[uint8, B]]\n",
            "a.py: A.x: reaches B, which does not exist at 3",
        ),
        (
            "@type(since=3)\nclass E(IntEnum, uint8):\n    A = 1\n\nclass B:\n    x: E\n",
            "a.py: B.x: reaches E, which does not exist at 1",
        ),
        (
            "class E(IntEnum, uint8):\n    A = value(1, since=3)\n\nclass B:\n    x: Literal[E.A]\n",
            "a.py: B.x: reaches E.A, which does not exist at 1",
        ),
        (
            "class E(IntEnum, uint8):\n    A = value(1, until=3)\n\nclass B:\n    x: bitset[E.A]\n",
            "a.py: B.x: reaches E.A, which does not exist at 3",
        ),
        (
            "class A:\n    class B:\n        pass\n\n    x: B\n\n@type(since=2)\nclass C:\n    pass\n\n"
            + "class D:\n    class E:\n        y: C\n",
            "a.py: D.E.y: reaches C, which does not exist at 1",
        ),
        (
            "@type(since=3)\nclass B:\n    pass\n\nclass A:\n    x: B | uint8\n",
            "a.py: A.x: reaches B, which does not exist at 1",
        ),
        (
            "@type(since=3)\nclass B:\n    pass\n\nclass A:\n    x: array[B, 2]\n",
            "a.py: A.x: reaches B, which does not exist at 1",
        ),
        (
            "@type(since=3)\nclass E(IntEnum, uint8):\n    X = 1\n\nclass A:\n    x: E = field(type=str)\n",
            "a.py: A.x: reaches E, which does not exist at 1",
        ),
        (
            "@type(since=3)\nclass E(IntEnum, uint8):\n    X = 1\n\nclass A:\n    x: dict[E, uint8]\n",
            "a.py: A.x: reaches E, which does not exist at 1",
        ),
        (
            "class E(IntEnum, uint8):\n    C = value(1, since=3)\n\n"
            + "class S:\n    k: E\n    x: uint8 = field(when=lambda p: p.k == E.C)\n",
            "a.py: S.x: reaches E.C, which does not exist at 1",
        ),
        (
            "class E(IntEnum, uint8):\n    A = 1\n    C = value(2, since=3)\n\n"
            + "class S:\n    b: bitset[E.A]\n    x: uint8 = field(when=lambda p: p.b.test(E.C))\n",
            "a.py: S.x: reaches E.C, which does not exist at 1",
        ),
        (
            "class E(IntEnum, uint8):\n    C = value(1, since=3)\n\n"
            + "class S:\n    k: E\n    with field(when=lambda p: p.k == E.C):\n        x: uint8 = field(since=3)\n"
            + "        y: uint8\n",
            "a.py: S.y: reaches E.C, which does not exist at 1",
        ),
        (
            "class E(IntEnum, uint8):\n    C = value(1, since=3)\n\n"
            + "class S:\n    k: E\n    x: uint8 = field(when=lambda p: not p.k == E.C)\n",
            "a.py: S.x: reaches E.C, which does not exist at 1",
        ),
    ],
)
def test_a_field_reaches_only_what_exists_where_it_is_present(build_package, source, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + source})


def test_a_nested_enum_is_checked(build_package):
    with pytest.raises(CompilerError, match=r"a\.py: A\.E\.X: has no earlier member to number from at 1"):
        build_package({"a": HEADER + "class A:\n    class E(IntEnum, uint8):\n        X = auto()\n"})


def test_a_field_gate_keeps_a_missing_type_out_of_its_range(build_package):
    build_package(
        {
            "a": HEADER
            + "@type(since=3)\nclass B:\n    pass\n\nclass E(IntEnum, uint8):\n    A = value(1, since=3)\n\n"
            + "class A:\n    x: B = field(since=3)\n    y: Literal[E.A] = field(since=3)\n"
            + "    z: bitset[E.A] = field(since=4)\n"
        }
    )


def test_a_reference_across_modules_is_checked(build_package):
    with pytest.raises(CompilerError, match=r"b\.py: A\.x: reaches B, which does not exist at 1"):
        build_package(
            {
                "a": HEADER + "@type(since=2)\nclass B:\n    pass\n",
                "b": HEADER + "from protocol.a import B\n\nclass A:\n    x: B\n",
            }
        )


@pytest.mark.parametrize(
    ("members", "message"),
    [
        ("A_B = 1\n    A_b = 2", "a.py: E: has the C\\+\\+ name AB twice at 1"),
        ("A = 1, 'x'\n    B = 2, 'X'", "a.py: E: has the wire name x twice at 1"),
        ("A_B = 1\n    AB = value(2, since=2, cpp_name='AB')", "a.py: E: has the C\\+\\+ name AB twice at 2"),
        ("A = auto()", "a.py: E.A: has no earlier member to number from at 1"),
        ("A = value(1, until=3)\n    B = value(since=2)", "a.py: E.B: has no earlier member to number from at 3"),
        ("A = value(1, until=3)\n    B = A", "a.py: E.B: names A, which does not exist at 3"),
    ],
)
def test_bad_enum_names_and_numbers_are_rejected(build_package, members, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + f"class E(IntEnum, uint8):\n    {members}\n"})


def test_names_that_never_meet_are_accepted(build_package):
    build_package(
        {
            "a": HEADER
            + "class E(IntEnum, uint8):\n    A = value(1, until=3)\n    A = value(2, since=3)\n"
            + "    A_B = value(3, until=3)\n    AB = value(4, since=3, cpp_name='AB')\n"
            + "    D = auto()\n"
        }
    )
