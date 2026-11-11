import pytest

from bedrock_protocol_compiler.descriptor import (
    Binary,
    CompilerError,
    EnumDeclaration,
    EnumRef,
    Int,
    Member,
    MemberRef,
    Primitive,
    Range,
)

HEADER = """
from enum import Enum, IntEnum, auto
from protocol import builtin, field, int8, int16, int32, int64, packet, type, uint8, uint16, uint32, uint64, value
package = "bedrock.protocol"
"""


def members(package):
    return package.modules[0].families[0].declarations[0].members


@pytest.mark.parametrize(
    ("bases", "underlying"),
    [
        ("IntEnum", None),
        ("Enum", None),
        ("IntEnum, uint8", Primitive("uint8")),
        ("Enum, int8", Primitive("int8")),
        ("IntEnum, int16", Primitive("int16")),
        ("IntEnum, uint16", Primitive("uint16")),
        ("IntEnum, int32", Primitive("int32")),
        ("Enum, uint32", Primitive("uint32")),
        ("IntEnum, bool", Primitive("bool")),
    ],
)
def test_bases_give_the_underlying_type(build_package, bases, underlying):
    package = build_package({"a": HEADER + f"class E({bases}):\n    A = 1\n"})

    assert package.modules[0].families[0].declarations == [EnumDeclaration(underlying, (members(package)[0],))]


def test_members_keep_source_order_and_literal_values(build_package):
    package = build_package({"a": HEADER + "class E(IntEnum, int8):\n    '''E.'''\n    B = 2\n    A = -1\n    C = 0\n"})

    assert [(member.name, member.value) for member in members(package)] == [
        ("B", Int(2)),
        ("A", Int(-1)),
        ("C", Int(0)),
    ]


def test_auto_and_bare_value_have_no_number(build_package):
    package = build_package(
        {"a": HEADER + "class E(IntEnum, uint8):\n    A = 1\n    B = auto()\n    C = value()\n    D = value(since=3)\n"}
    )

    assert [member.value for member in members(package)] == [Int(1), None, None, None]
    assert members(package)[3].range == Range(3, None)


def test_value_carries_a_number_and_a_range(build_package):
    package = build_package(
        {
            "a": HEADER
            + "class E(IntEnum, uint8):\n"
            + "    A = value(5, since=2)\n    B = value(6, until=3)\n    C = value(7, since=1, until=3)\n    D = 8\n"
        }
    )

    assert members(package) == (
        Member("A", Int(5), Range(2, None), None, None),
        Member("B", Int(6), Range(None, 3), None, None),
        Member("C", Int(7), Range(1, 3), None, None),
        Member("D", Int(8), Range(None, None), None, None),
    )


def test_pair_and_value_name_give_the_wire_name(build_package):
    package = build_package(
        {
            "a": HEADER
            + "class E(Enum, uint8):\n    A = 1, 'a_name'\n    B = value(2, 'b_name')\n"
            + "class F(IntEnum, uint8):\n    A = 1, 'a_name'\n"
        }
    )

    assert [(member.value, member.wire_name) for member in members(package)] == [
        (Int(1), "a_name"),
        (Int(2), "b_name"),
    ]
    assert package.modules[0].families[1].declarations[0].members[0].wire_name == "a_name"


def test_cpp_name_is_a_case_variant(build_package):
    package = build_package(
        {"a": HEADER + "class E(IntEnum, uint8):\n    NPC_REQUEST = value(3, cpp_name='NPCRequest')\n"}
    )

    assert members(package)[0].cpp_name == "NPCRequest"


def test_siblings_resolve_to_earlier_members(build_package):
    package = build_package(
        {
            "a": HEADER
            + "class E(IntEnum, uint8):\n    A = 1\n    COUNT = A\n    LATEST = COUNT - 1\n    NEXT = value(A)\n"
        }
    )

    enum = package.modules[0].families[0]

    assert [member.value for member in members(package)] == [
        Int(1),
        MemberRef(enum, "A"),
        Binary("-", MemberRef(enum, "COUNT"), Int(1)),
        MemberRef(enum, "A"),
    ]


def test_a_member_moves_value_across_disjoint_ranges(build_package):
    package = build_package(
        {
            "a": HEADER
            + "class E(IntEnum, uint8):\n    A = value(1, until=3)\n    A = value(2, since=3, until=5)\n"
            + "    A = value(3, since=5)\n"
        }
    )

    assert [(member.value, member.range) for member in members(package)] == [
        (Int(1), Range(None, 3)),
        (Int(2), Range(3, 5)),
        (Int(3), Range(5, None)),
    ]


def test_nested_enum_is_owned_and_referenced(build_package):
    package = build_package(
        {
            "a": HEADER
            + "class A:\n    class E(IntEnum, uint8):\n        X = 1\n    e: E\n"
            + "class B:\n    e: A.E\n"
            + "@type()\nclass E2(IntEnum, uint8):\n    X = 1\n"
        }
    )

    a, b, e2 = package.modules[0].families
    nested = a.nested[0]

    assert (nested.name, nested.owner, nested.module) == ("E", a, "a")
    assert a.declarations[0].fields[0].type == EnumRef(nested)
    assert b.declarations[0].fields[0].type == EnumRef(nested)
    assert e2.owner is None


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("class E(uint8):\n    A = 1\n", "E: is not IntEnum or Enum"),
        ("class E(IntEnum, IntEnum):\n    A = 1\n", "IntEnum: is not a type"),
        ("class E(IntEnum, uint64):\n    A = 1\n", "E: is not an enum underlying type"),
        ("class E(IntEnum, str):\n    A = 1\n", "E: is not an enum underlying type"),
        ("class E(IntEnum, uint8, uint8):\n    A = 1\n", "E: takes an enum base and at most"),
        ("@packet(id=1)\nclass E(IntEnum):\n    A = 1\n", "E: an enum takes no decorator but type"),
        ("@builtin\nclass E(IntEnum):\n    A = 1\n", "E: an enum takes no decorator but type"),
        ("class E(IntEnum):\n    pass\n", "E: has no members"),
        ("class E(IntEnum):\n    A = 1\n    x: uint8\n", "E: holds only members"),
        ("class E(IntEnum):\n    A = 1\n    class B:\n        pass\n", "E: holds only members"),
        ("class E(IntEnum):\n    A = B = 1\n", "E: holds only members"),
        ("class E(IntEnum):\n    A = 'x'\n", "A: is not a int literal"),
        ("class E(IntEnum):\n    A = True\n", "A: is not a int literal"),
        ("class E(IntEnum):\n    A = 1.5\n", "A: is not a int literal"),
        ("class E(IntEnum):\n    A = 1, 'a', 'b'\n", "A: a pair is a value and a wire name"),
        ("class E(IntEnum):\n    A = 1, 2\n", "A: is not a str literal"),
        ("class E(IntEnum):\n    A = 1, ''\n", "A: is an empty string"),
        (
            "class E(IntEnum):\n    A = value(1, 'x', name='y')\n",
            "value: got .* 'name'",
        ),
        (
            "class E(IntEnum):\n    A = (value(1, 'x'), 'y')\n",
            "A: has its wire name twice",
        ),
        ("class E(IntEnum):\n    A = value(1, cpp_name='B')\n", "A: cpp_name 'B' is not a case variant"),
        ("class E(IntEnum):\n    A_B = value(1, cpp_name='')\n", "A_B: is an empty string"),
        ("class E(IntEnum):\n    A = value(1, since='2')\n", "A: is not a int literal"),
        ("class E(IntEnum):\n    A = value(1, bogus=2)\n", "value: got an unexpected keyword argument 'bogus'"),
        ("class E(IntEnum):\n    A = value(*[1])\n", "value: takes its arguments written out"),
        ("class E(IntEnum):\n    A = B\n    B = 1\n", "A: B is not a member declared above it"),
        ("class E(IntEnum):\n    A = A\n", "A: A is not a member declared above it"),
        ("class E(IntEnum):\n    A = 1\n    B = A + 1\n", "B: is not a member minus an integer"),
        ("class E(IntEnum):\n    A = 1\n    B = 1 - A\n", "B: is not a member minus an integer"),
        ("class E(IntEnum):\n    A = 1\n    B = A - 'x'\n", "B: is not a int literal"),
        ("class E(IntEnum):\n    A = auto(1)\n", "A: is not a int literal"),
        ("class E(IntEnum):\n    A = 1\n    A = 2\n", "A: is declared twice over overlapping versions"),
        ("class E(IntEnum):\n    A = value(1, until=3)\n    A = value(2, since=2)\n", "A: is declared twice over"),
        ("class E(IntEnum):\n    A = value(1, since=2)\n    A = value(2, until=3)\n", "A: is declared twice over"),
        ("class E(IntEnum):\n    A = 1\n    A = value(2, since=2)\n", "A: is declared twice over"),
        (
            "class E(IntEnum):\n    A = value(1, since=3, until=5)\n    A = value(1, since=4)\n",
            "A: is declared twice over",
        ),
        ("class E(IntEnum):\n    A = print(1)\n", "A: is not a int literal"),
        ("class A:\n    class E(IntEnum):\n        pass\n", "E: has no members"),
        ("class E(IntEnum):\n    A = 1\nclass E(IntEnum):\n    A = 1\n", "E: is already declared"),
    ],
)
def test_bad_enum_is_rejected(build_package, source, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + source})


def test_adjacent_ranges_do_not_overlap(build_package):
    package = build_package(
        {"a": HEADER + "class E(IntEnum, uint8):\n    A = value(1, until=3)\n    A = value(2, since=3)\n"}
    )

    assert len(members(package)) == 2
