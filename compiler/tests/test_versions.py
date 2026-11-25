import pytest

from bedrock_protocol_compiler.descriptor import CompilerError, Int, Primitive, Range, Variant

HEADER = """
from enum import IntEnum, auto
from typing import Literal
from protocol import array, bitset, field, packet, sentinel, type, uint8, uint16, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"
"""

GATED_ALIAS = (
    "with type(until=3):\n    type V = uint8 | uint16\n\nwith type(since=3):\n    type V = uint8 | uint16 | bool\n\n"
)
NARROW = Variant((Primitive("uint8"), Primitive("uint16")))
WIDE = Variant((Primitive("uint8"), Primitive("uint16"), Primitive("bool")))


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
        ("class E(IntEnum, uint8):\n    A = value(1, until=9)\n", "A: until 9 is not a modelled version"),
        ("@type(since=3, until=3)\nclass A:\n    pass\n", "A: has an empty version range"),
        ("class A:\n    x: uint8 = field(since=4, until=2)\n", "x: has an empty version range"),
        (
            "@type(since=2)\nclass A:\n    x: uint8 = field(since=2)\n",
            "x: has a gate its enclosing range already decides",
        ),
        (
            "@type(since=2)\nclass A:\n    x: uint8 = field(since=1)\n",
            "x: has a gate its enclosing range already decides",
        ),
        (
            "@type(until=3)\nclass A:\n    x: uint8 = field(until=3)\n",
            "x: has a gate its enclosing range already decides",
        ),
        (
            "@type(until=3)\nclass A:\n    x: uint8 = field(since=3)\n",
            "x: has a gate its enclosing range already decides",
        ),
        (
            "@type(since=3)\nclass A:\n    x: uint8 = field(until=3)\n",
            "x: has a gate its enclosing range already decides",
        ),
        ("class A:\n    with field(since=4, until=2):\n        x: uint8\n", "A: has an empty version range"),
        ("class A:\n    with field(since=9):\n        x: uint8\n", "A: since 9 is not a modelled version"),
        ("@type(since=2)\nclass A:\n    with field(since=2):\n        x: uint8\n", "A: has a gate its enclosing range"),
        ("@type(until=3)\nclass A:\n    with field(since=3):\n        x: uint8\n", "A: has a gate its enclosing range"),
        (
            "class A:\n    with field(since=2):\n        x: uint8 = field(since=2)\n",
            "x: has a gate its enclosing range already decides",
        ),
        (
            "class A:\n    with field(until=4):\n        x: uint8 = field(since=4)\n",
            "x: has a gate its enclosing range already decides",
        ),
        (
            "class A:\n    with field(since=2):\n        x: uint8 = field(since=1)\n",
            "x: has a gate its enclosing range already decides",
        ),
        (
            "class A:\n    with field(since=2):\n        with field(until=4):\n            x: uint8\n",
            "A: a with block holds only fields",
        ),
        (
            "@type(until=3)\nclass E(IntEnum, uint8):\n    A = value(1, until=4)\n",
            "A: has a gate its enclosing range already decides",
        ),
        (
            "class E(IntEnum, uint8):\n    A = value(1, unnamed_since=9)\n",
            "A: unnamed_since 9 is not a modelled version",
        ),
        (
            "class E(IntEnum, uint8):\n    A = value(1, since=3, unnamed_since=2)\n",
            "A: unnamed_since 2 is outside its version range",
        ),
        (
            "class E(IntEnum, uint8):\n    A = value(1, until=3, unnamed_since=3)\n",
            "A: unnamed_since 3 is outside its version range",
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


def test_a_field_naming_a_gated_union_alias_takes_each_declaration_over_its_range(build_package):
    package = build_package({"a": HEADER + GATED_ALIAS + "class A:\n    x: V\n"})

    fields = package.modules[0].families[0].declarations[0].fields

    assert [(field.type, field.range) for field in fields] == [(NARROW, Range(None, 3)), (WIDE, Range(3, None))]


def test_a_field_within_one_declaration_of_a_gated_union_alias_stays_whole(build_package):
    package = build_package({"a": HEADER + GATED_ALIAS + "class A:\n    x: V = field(since=3)\n"})

    fields = package.modules[0].families[0].declarations[0].fields

    assert [(field.type, field.range) for field in fields] == [(WIDE, Range(3, None))]


def test_a_union_alias_naming_a_gated_one_splits_a_field_at_the_inner_gate(build_package):
    package = build_package({"a": HEADER + GATED_ALIAS + "type W = V | str\n\nclass A:\n    x: W\n"})

    fields = package.modules[0].families[0].declarations[0].fields

    assert [(field.type, field.range) for field in fields] == [
        (Variant((NARROW, Primitive("str"))), Range(None, 3)),
        (Variant((WIDE, Primitive("str"))), Range(3, None)),
    ]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "with type(until=2):\n    type V = uint8 | uint16\n\nwith type(since=3):\n    type V = uint8 | bool\n",
            "V: starts at 3, but its previous declaration ends at 2",
        ),
        ("type V = uint8 | uint16\n\ntype V = uint8 | bool\n", "V: is declared again after an open declaration"),
        ("with type(since=3):\n    type V = uint8\n", "V: is a primitive alias, which takes no gate"),
        (
            "with type(cereal=False):\n    type V = uint8 | uint16\n",
            "module: a with block takes only since= and until=",
        ),
        ("with type(since=3):\n    class A:\n        pass\n", "module: a with block holds only type aliases"),
        ("with type(since=9):\n    type V = uint8 | uint16\n", "module: since 9 is not a modelled version"),
        ("with type(since=3):\n    type V = uint8 | uint16\n\ntype W = V | bool\n", "V: does not exist at 1"),
    ],
)
def test_a_union_alias_declaration_is_rejected(build_package, source, message):
    with pytest.raises(CompilerError, match=message):
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
    source = "@type(until=3)\nclass A:\n    pass\n\n@type(since=3)\nclass A(IntEnum, uint8):\n    B = 1\n"

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


def test_the_pre_cereal_flavour_of_a_name_shared_by_two_modules_is_rejected(build_package):
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


def test_the_pre_cereal_flavour_is_redeclared_beside_its_cereal_family(build_package):
    package = build_package(
        {
            "a": HEADER
            + "class A:\n    pass\n\n"
            + "@type(cereal=False, until=2)\nclass A:\n    pass\n\n"
            + "@type(cereal=False, since=2)\nclass A:\n    pass\n"
        }
    )

    pre_cereal = package.modules[0].families[1]

    assert [declaration.range for declaration in pre_cereal.declarations] == [Range(None, 2), Range(2, None)]


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


@pytest.mark.parametrize(
    "source",
    [
        "@type(since=2)\nclass A:\n    @type(since=2)\n    class B:\n        pass\n",
        "@type(since=2)\nclass A:\n    @type(since=1)\n    class B:\n        pass\n",
        "@type(until=3)\nclass A:\n    @type(until=3)\n    class B:\n        pass\n",
        "@type(until=3)\nclass A:\n    @type(until=4)\n    class B(IntEnum, uint8):\n        C = 1\n",
    ],
)
def test_a_nested_gate_its_owner_decides_is_rejected(build_package, source):
    with pytest.raises(CompilerError, match="B: has a gate its enclosing range already decides"):
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
        ("with type(since=3):\n    type V = uint8 | uint16\n\nclass S:\n    x: V\n", "V: does not exist at 1"),
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
        ("A = auto()", "a.py: E.A: has no earlier member to number from at 1"),
        ("A = sentinel()", "a.py: E.A: has no earlier member to number from at 1"),
        ("A = value(1, until=3)\n    B = value(since=2)", "a.py: E.B: has no earlier member to number from at 3"),
        ("A = value(1, until=3)\n    B = A", "a.py: E.B: names A, which does not exist at 3"),
        (
            "A = value(1, until=3)\n    B = A\n    A = value(5, since=3)",
            "a.py: E.B: names A, which does not exist at 3",
        ),
    ],
)
def test_bad_enum_names_and_numbers_are_rejected(build_package, members, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + f"class E(IntEnum, uint8):\n    {members}\n"})


@pytest.mark.parametrize(
    ("members", "message"),
    [
        pytest.param(
            "A_B = 1\n    A_b = 2",
            "a.py: E: has the C\\+\\+ name AB on A_B and A_b",
            id="c++ names that fold to one",
        ),
        pytest.param(
            "A = 1, 'x'\n    B = 2, 'X'",
            "a.py: E: has the encoded name x on A and B",
            id="encoded names that fold to one",
        ),
        pytest.param(
            "A_B = value(3, until=3)\n    AB = value(4, since=3, cpp_name='AB')",
            "a.py: E: has the C\\+\\+ name AB on A_B and AB",
            id="c++ name in versions that never meet",
        ),
        pytest.param(
            "A = value(1, 'x', until=3)\n    B = value(2, 'x', since=3)",
            "a.py: E: has the encoded name x on A and B",
            id="encoded name in versions that never meet",
        ),
    ],
)
def test_a_spelling_two_members_hold_is_rejected(build_package, members, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + f"class E(IntEnum, uint8):\n    {members}\n"})


@pytest.mark.parametrize(
    ("source", "message"),
    [
        pytest.param(
            "class E(IntEnum, uint8):\n    A = 1, 'x'\n\n"
            "@type(cereal=False)\nclass E(IntEnum, uint8):\n    B = 1, 'x'\n",
            "a.py: E: has the encoded name x on A and B",
            id="module-scope enum",
        ),
        pytest.param(
            "class A:\n    class E(IntEnum, uint8):\n        A = 1, 'x'\n    e: E\n\n"
            "@type(cereal=False)\nclass A:\n    class E(IntEnum, uint8):\n        B = 1, 'x'\n    e: E\n",
            "a.py: A.E: has the encoded name x on A and B",
            id="nested enum",
        ),
    ],
)
def test_a_spelling_an_enum_shares_with_its_pre_cereal_sibling_is_rejected(build_package, source, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + source})


def test_a_member_redeclared_across_versions_is_accepted(build_package):
    build_package({"a": HEADER + "class E(IntEnum, uint8):\n    A = value(1, until=3)\n    A = value(2, since=3)\n"})


@pytest.mark.parametrize(
    ("source", "message"),
    [
        pytest.param(
            "class E(IntEnum, uint8):\n    A = 1\n    B = 2\n    C = value(3, until=3)\n    C = value(4, since=3)\n"
            "    X = C - 1\n",
            r"a\.py: E\.X: takes the number 3, which no member that is neither an alias nor a sentinel holds at 3",
            id="offset alias",
        ),
        pytest.param(
            "class E(IntEnum, uint8):\n    A = 1\n    COUNT = sentinel()\n    LATEST = COUNT\n",
            r"a\.py: E\.LATEST: takes the number 2, which no member that is neither an alias nor a sentinel holds at 1",
            id="alias of a sentinel",
        ),
        pytest.param(
            "@type(until=3)\nclass E(IntEnum, uint8):\n    A = 1\n    L = 5\n\n"
            "@type(since=3)\nclass E(IntEnum, uint8):\n    A = 1\n    L = A\n",
            r"a\.py: E\.L: takes the number 5, which no member that is neither an alias nor a sentinel holds at 1",
            id="alias in its newest declaration",
        ),
        pytest.param(
            "class A:\n    class E(IntEnum, uint8):\n        A = 1\n        X = A - 1\n    e: E\n",
            r"a\.py: A\.E\.X: takes the number 0, which no member that is neither an alias nor a sentinel holds at 1",
            id="nested enum",
        ),
    ],
)
def test_an_alias_whose_number_no_other_member_holds_is_rejected(build_package, source, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + source})


def test_an_alias_whose_number_another_member_holds_at_every_version_is_accepted(build_package):
    source = (
        "class E(IntEnum, uint8):\n    A = 0\n    B = 1\n    C = value(2, since=3)\n    COUNT = sentinel()\n"
        "    LATEST = COUNT - 1\n"
    )
    build_package({"a": HEADER + source})


def test_two_members_sharing_a_number_at_a_version_are_rejected(build_package):
    message = r"^a\.py: E\.B: shares the number 1 with A at 1 and is neither derived nor a synonym$"
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = 1\n"})


def test_a_synonym_sharing_its_number_with_no_other_member_is_rejected(build_package):
    message = r"^a\.py: E\.B: is a synonym but shares its number with no other member at any version$"
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = value(2, synonym=True)\n"})


@pytest.mark.parametrize(
    "members",
    [
        pytest.param("    A = 1\n    B = value(1, synonym=True)\n", id="synonym"),
        pytest.param("    A = 1\n    B = A\n", id="derived"),
        pytest.param("    A = value(1, until=3)\n    B = value(1, since=3)\n", id="never live together"),
        pytest.param("    A = value(1, until=3)\n    B = value(1, synonym=True)\n", id="synonym at some versions"),
    ],
)
def test_a_member_sharing_a_number_is_accepted_as_a_synonym_a_pointer_or_a_renumbering(build_package, members):
    build_package({"a": HEADER + "class E(IntEnum, uint8):\n" + members})


def test_a_block_gives_each_field_its_range(build_package):
    source = (
        "class A:\n    a: uint8\n    with field(since=2, until=5):\n        x: uint8\n"
        "        y: uint8 = field(since=3)\n        z: uint8 = field(until=4)\n"
    )
    package = build_package({"a": HEADER + source})

    assert [field.range for field in package.modules[0].families[0].declarations[0].fields] == [
        Range(None, None),
        Range(2, 5),
        Range(3, 5),
        Range(2, 4),
    ]


def test_a_block_is_clipped_to_its_declaration(build_package):
    source = "@type(since=2, until=5)\nclass A:\n    with field(since=3, until=4):\n        x: uint8\n"
    package = build_package({"a": HEADER + source})

    assert package.modules[0].families[0].declarations[0].fields[0].range == Range(3, 4)


def test_an_enum_block_gives_each_member_its_range(build_package):
    source = (
        "class E(IntEnum, uint8):\n    A = 1\n    with value(since=2, until=5):\n        B = 2\n"
        "        C = value(3, since=3)\n        D = value(4, until=4)\n"
    )
    package = build_package({"a": HEADER + source})

    assert [member.range for member in package.modules[0].families[0].declarations[0].members] == [
        Range(None, None),
        Range(2, 5),
        Range(3, 5),
        Range(2, 4),
    ]


def test_a_value_carries_its_unnamed_since(build_package):
    package = build_package({"a": HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = value(2, unnamed_since=3)\n"})

    assert [member.unnamed_since for member in package.modules[0].families[0].declarations[0].members] == [None, 3]


def test_an_unnamed_value_may_carry_its_bds_spelling_ungated(build_package):
    package = build_package({"a": HEADER + "class E(IntEnum, uint8):\n    A = value(1, 'Aye', unnamed_since=3)\n"})

    assert package.modules[0].families[0].declarations[0].members[0].encoded_name == "aye"


def test_an_enum_block_gives_each_member_its_unnamed_since(build_package):
    source = (
        "class E(IntEnum, uint8):\n    A = 1\n    with value(since=2, unnamed_since=3):\n        B = 2\n"
        "        C = auto()\n    D = auto()\n"
    )
    members = build_package({"a": HEADER + source}).modules[0].families[0].declarations[0].members

    assert [member.unnamed_since for member in members] == [None, 3, 3, None]


def test_a_pair_and_auto_inside_an_enum_block(build_package):
    source = (
        "class E(IntEnum, uint8):\n    A = 1\n    with value(since=3):\n        B = 2, 'Bee'\n"
        "        C = auto()\n    D = auto()\n"
    )
    members = build_package({"a": HEADER + source}).modules[0].families[0].declarations[0].members

    assert [(member.name, member.value, member.encoded_name, member.range) for member in members] == [
        ("A", Int(1), "a", Range(None, None)),
        ("B", Int(2), "bee", Range(3, None)),
        ("C", None, "c", Range(3, None)),
        ("D", None, "d", Range(None, None)),
    ]


def test_a_sentinel_inside_an_enum_block_takes_its_gate(build_package):
    source = (
        "class E(IntEnum, uint8):\n    A = 1\n    with value(until=3):\n        B = sentinel()\n"
        "    B = value(since=3)\n"
    )
    members = build_package({"a": HEADER + source}).modules[0].families[0].declarations[0].members

    assert [(member.name, member.sentinel, member.range) for member in members] == [
        ("A", False, Range(None, None)),
        ("B", True, Range(None, 3)),
        ("B", False, Range(3, None)),
    ]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "@type(until=3)\nclass E(IntEnum, uint8):\n    with value(until=4):\n        A = 1\n",
            "E: has a gate its enclosing range already decides",
        ),
        (
            "class E(IntEnum, uint8):\n    with value(since=2):\n        A = value(1, since=2)\n",
            "A: has a gate its enclosing range already decides",
        ),
        (
            "class E(IntEnum, uint8):\n    with value(since=2):\n        with value(until=4):\n            A = 1\n",
            "E: a with block holds only members",
        ),
        (
            "class E(IntEnum, uint8):\n    with value():\n        A = 1\n",
            "E: a with block takes only since=, until= and unnamed_since=",
        ),
        (
            "class E(IntEnum, uint8):\n    with value(since=3, unnamed_since=2):\n        A = 1\n",
            "A: unnamed_since 2 is outside its version range",
        ),
        (
            "class E(IntEnum, uint8):\n    with value(since=2):\n        A = value(1, 'Aye')\n",
            "A: a member without its own gate takes a pair, not value\\(\\)",
        ),
    ],
)
def test_a_bad_enum_block_is_rejected(build_package, source, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + source})


def test_a_field_declared_twice_over_disjoint_gates_changes_type_in_place(build_package):
    package = build_package(
        {
            "a": HEADER
            + "class A:\n    a: uint8\n    x: uint8 = field(until=3)\n    x: uint16 = field(since=3)\n    z: uint8\n"
        }
    )

    (family,) = package.modules[0].families
    fields = family.declarations[0].fields

    assert [(each.name, each.type.name, each.range) for each in fields] == [
        ("a", "uint8", Range(None, None)),
        ("x", "uint8", Range(None, 3)),
        ("x", "uint16", Range(3, None)),
        ("z", "uint8", Range(None, None)),
    ]


def test_a_one_field_twin_inside_a_with_block_is_accepted(build_package):
    package = build_package(
        {
            "a": HEADER
            + "class A:\n    with field(since=2):\n        a: uint8\n        x: uint8 = field(until=3)\n"
            + "        x: uint16 = field(since=3)\n    z: uint8\n"
        }
    )

    fields = package.modules[0].families[0].declarations[0].fields

    assert [(each.name, each.type.name, each.range) for each in fields] == [
        ("a", "uint8", Range(2, None)),
        ("x", "uint8", Range(2, 3)),
        ("x", "uint16", Range(3, None)),
        ("z", "uint8", Range(None, None)),
    ]


def test_a_run_declared_twice_over_disjoint_blocks_changes_types_in_place(build_package):
    package = build_package(
        {
            "a": HEADER
            + "class A:\n    with field(until=3):\n        x: uint8\n        y: uint8\n"
            + "    with field(since=3):\n        x: uint16\n        y: uint16\n    z: uint8\n"
        }
    )

    (family,) = package.modules[0].families
    fields = family.declarations[0].fields

    assert [(each.name, each.type.name, each.range) for each in fields] == [
        ("x", "uint8", Range(None, 3)),
        ("y", "uint8", Range(None, 3)),
        ("x", "uint16", Range(3, None)),
        ("y", "uint16", Range(3, None)),
        ("z", "uint8", Range(None, None)),
    ]


def test_a_twin_is_clipped_to_its_declaration(build_package):
    package = build_package(
        {
            "a": HEADER
            + "@type(since=2, until=5)\nclass A:\n    x: uint8 = field(until=3)\n    x: uint16 = field(since=3)\n"
        }
    )

    fields = package.modules[0].families[0].declarations[0].fields

    assert [each.range for each in fields] == [Range(2, 3), Range(3, 5)]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "class A:\n    x: uint8 = field(until=3)\n    x: uint16 = field(since=2)\n",
            "x: is declared twice over overlapping versions",
        ),
        (
            "class A:\n    with field(until=3):\n        x: uint8\n    with field(since=2):\n        x: uint16\n",
            "x: is declared twice over overlapping versions",
        ),
        (
            "class A:\n    x: uint8 = field(until=3)\n    y: uint8\n    x: uint16 = field(since=3)\n",
            "x: is declared twice away from its first declaration",
        ),
        (
            "class A:\n    with field(until=3):\n        x: uint8\n        y: uint8\n"
            + "    with field(since=3):\n        y: uint8\n        x: uint8\n",
            "y: is declared twice in a block that does not repeat the block above it in order",
        ),
        (
            "class A:\n    with field(until=3):\n        x: uint8\n        y: uint8\n"
            + "    with field(since=3):\n        x: uint8\n",
            "x: is declared twice in a block that does not repeat the block above it in order",
        ),
        (
            "class A:\n    x: uint8 = field(until=3)\n    y: uint8 = field(until=3)\n"
            + "    x: uint16 = field(since=3)\n    y: uint16 = field(since=3)\n",
            "x: is declared twice away from its first declaration",
        ),
        (
            "class A:\n    with field(until=3):\n        x: uint8\n"
            + "    with field(since=3):\n        a: uint8\n        x: uint16\n",
            "x: is declared twice in a block that does not repeat the block above it in order",
        ),
    ],
)
def test_a_malformed_twin_is_rejected(build_package, source, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + source})
