import pytest

from bedrock_protocol_compiler.descriptor import Binary, CompilerError, FieldRef, Int, Len, MemberRef, Not, Range, Test

HEADER = """
from enum import IntEnum
from protocol import bitset, field, packet, type, uint8, uint32, value
package = "bedrock.protocol"

class E(IntEnum, uint8):
    A = 1
    B = 2
    C = value(3, since=3)
"""


def family_of(package, name="S"):
    return next(family for family in package.modules[0].families if family.name == name)


def when_of(package, name):
    return next(field.when for field in family_of(package).declarations[0].fields if field.name == name)


def test_a_field_reads_an_earlier_field_and_an_enum_member(build_package):
    source = HEADER + "class S:\n    k: E\n    x: uint8 = field(when=lambda p: p.k == E.A)\n"
    package = build_package({"a": source})

    assert when_of(package, "x") == Binary("==", FieldRef("k"), MemberRef(family_of(package, "E"), "A"))


def test_the_parameter_may_have_any_name(build_package):
    package = build_package({"a": HEADER + "class S:\n    k: uint8\n    x: uint8 = field(when=lambda q: q.k)\n"})

    assert when_of(package, "x") == FieldRef("k")


def test_a_predicate_takes_not_and_or_and_comparisons(build_package):
    source = HEADER + (
        "class S:\n    k: uint8\n    j: uint8\n"
        "    x: uint8 = field(when=lambda p: not p.k != 1 or p.j < -2 and p.k & 4 == 0)\n"
    )
    package = build_package({"a": source})

    assert when_of(package, "x") == Binary(
        "or",
        Not(Binary("!=", FieldRef("k"), Int(1))),
        Binary(
            "and",
            Binary("<", FieldRef("j"), Int(-2)),
            Binary("==", Binary("&", FieldRef("k"), Int(4)), Int(0)),
        ),
    )


def test_in_a_set_is_an_or_of_equalities(build_package):
    source = HEADER + "class S:\n    k: E\n    x: uint8 = field(when=lambda p: p.k in {E.A, E.B})\n"
    package = build_package({"a": source})
    enum = family_of(package, "E")

    assert when_of(package, "x") == Binary(
        "or",
        Binary("==", FieldRef("k"), MemberRef(enum, "A")),
        Binary("==", FieldRef("k"), MemberRef(enum, "B")),
    )


def test_a_bit_test_names_a_bitset_field_and_a_member(build_package):
    source = HEADER + "class S:\n    bits: bitset[E.B]\n    x: uint8 = field(when=lambda p: p.bits.test(E.A))\n"
    package = build_package({"a": source})

    assert when_of(package, "x") == Test("bits", MemberRef(family_of(package, "E"), "A"))


def test_a_nested_enum_is_named_bare_or_through_its_owner(build_package):
    source = HEADER + (
        "class S:\n    class N(IntEnum, uint8):\n        Z = 1\n\n"
        "    k: N\n"
        "    x: uint8 = field(when=lambda p: p.k == N.Z)\n"
        "    y: uint8 = field(when=lambda p: p.k == S.N.Z)\n"
    )
    package = build_package({"a": source})

    assert when_of(package, "x") == when_of(package, "y")


def test_a_with_block_gives_each_field_its_predicate(build_package):
    source = HEADER + (
        "class S:\n    k: uint8\n    with field(when=lambda p: p.k == 1):\n        x: uint8\n        y: uint8\n"
        "    z: uint8\n"
    )
    package = build_package({"a": source})

    assert [field.when for field in family_of(package).declarations[0].fields] == [
        None,
        Binary("==", FieldRef("k"), Int(1)),
        Binary("==", FieldRef("k"), Int(1)),
        None,
    ]


def test_a_field_and_its_block_both_guard(build_package):
    source = HEADER + (
        "class S:\n    k: uint8\n    with field(when=lambda p: p.k == 1):\n"
        "        x: uint8 = field(when=lambda p: p.k == 2)\n"
    )
    package = build_package({"a": source})

    assert family_of(package).declarations[0].fields[1].when == Binary(
        "and", Binary("==", FieldRef("k"), Int(1)), Binary("==", FieldRef("k"), Int(2))
    )


def test_a_block_takes_a_gate_beside_its_guard(build_package):
    source = HEADER + ("class S:\n    k: E\n    with field(since=3, when=lambda p: p.k == E.C):\n        x: uint8\n")
    package = build_package({"a": source})
    block_field = family_of(package).declarations[0].fields[1]

    assert block_field.range == Range(3, None)
    assert block_field.when == Binary("==", FieldRef("k"), MemberRef(family_of(package, "E"), "C"))


def test_a_guard_in_a_gated_block_names_a_field_the_block_gates(build_package):
    source = HEADER + (
        "class S:\n    with field(since=2):\n        k: uint8\n        x: uint8 = field(when=lambda p: p.k == 1)\n"
    )
    package = build_package({"a": source})

    assert when_of(package, "x") == Binary("==", FieldRef("k"), Int(1))


def test_count_is_a_field_a_length_or_a_product(build_package):
    source = HEADER + (
        "class S:\n    n: uint8\n    xs: list[uint8] = field(count=lambda p: p.n)\n"
        "    ys: list[uint8] = field(count=lambda p: len(p.xs))\n"
        "    zs: list[uint8] = field(count=lambda p: p.n * p.n)\n"
    )
    package = build_package({"a": source})
    counts = [field.type.count for field in family_of(package).declarations[0].fields[1:]]

    assert counts == [FieldRef("n"), Len("xs"), Binary("*", FieldRef("n"), FieldRef("n"))]
    assert [field.type.prefix for field in family_of(package).declarations[0].fields[1:]] == [None, None, None]


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("x: uint8 = field(when=lambda p: p.k)\n    k: uint8", "x: p.k is not an earlier field"),
        ("k: uint8\n    x: uint8 = field(when=lambda p: p.q)", "x: p.q is not an earlier field"),
        ("k: uint8\n    x: uint8 = field(when=lambda: 1)", "x: is not a lambda of one argument"),
        ("k: uint8\n    x: uint8 = field(when=lambda p, q: 1)", "x: is not a lambda of one argument"),
        ("k: uint8\n    x: uint8 = field(when=1)", "x: is not a lambda of one argument"),
        ("k: uint8\n    x: uint8 = field(when=lambda p: p.k + 1)", "x: is not a predicate"),
        ("k: uint8\n    x: uint8 = field(when=lambda p: 1 < p.k < 3)", "x: is not a predicate"),
        ("k: uint8\n    x: uint8 = field(when=lambda p: p.k >= 1)", "x: is not a predicate"),
        ("k: uint8\n    x: uint8 = field(when=lambda p: p.k not in {1})", "x: is not a predicate"),
        ("k: uint8\n    x: uint8 = field(when=lambda p: p.k in [1])", "x: is not a predicate"),
        ("k: uint8\n    x: uint8 = field(when=lambda p: len(p.k))", "x: is not a predicate"),
        (
            "k: uint8\n    x: uint8 = field(when=lambda p: p.k.test(E.A))",
            "x: test is given something other than a bitset",
        ),
        ("k: uint8\n    x: uint8 = field(when=lambda p: p.k == E.Z)", "E.Z: is not an enum member"),
        ("k: uint8\n    x: uint8 = field(when=lambda p: p.k == Q.A)", "Q: is not defined"),
        ("k: uint8\n    x: uint8 = field(when=lambda p: q.k)", "q: is not defined"),
        ("k: uint8 = field(since=2)\n    x: uint8 = field(when=lambda p: p.k)", "x: p.k is absent at 1"),
        ("k: uint8 = field(until=4)\n    x: uint8 = field(when=lambda p: p.k)", "x: p.k is absent at 4"),
        ("k: uint8\n    x: uint8 = field(when=lambda p: p.k, count=lambda p: p.k)", "x: count is given to something"),
        (
            "k: uint8\n    x: list[uint8] = field(prefix=uint32, count=lambda p: p.k)",
            "x: count and prefix are both given",
        ),
        ("k: uint8\n    x: list[uint8] | None = field(count=lambda p: p.k)", "x: count is given to something"),
        (
            "k: uint8\n    x: list[uint8] = field(count=lambda p: p.k + 1)",
            "x: is not a field, len\\(field\\) or a product",
        ),
        ("k: uint8\n    x: list[uint8] = field(count=lambda p: len(p.k))", "x: len is given something other"),
        (
            "k: uint8\n    with field(when=lambda p: p.k):\n        class N:\n            pass",
            "S: a with block holds only fields",
        ),
        ("k: uint8\n    with field(when=lambda p: p.k):\n        pass", "S: a with block holds only fields"),
        (
            "k: uint8\n    with field(when=lambda p: p.k):\n"
            + "        with field(when=lambda p: p.k):\n            x: uint8",
            "S: a with block holds only fields",
        ),
        ("k: uint8\n    with field():\n        x: uint8", "S: a with block takes only since="),
        (
            "k: uint8\n    with field(when=lambda p: p.k, type=uint8):\n        x: uint8",
            "S: a with block takes only since=",
        ),
        (
            "k: uint8\n    with field(when=lambda p: p.k) as g:\n        x: uint8",
            "S: is not a with field\\(...\\) block",
        ),
        (
            "k: uint8\n    with field(when=lambda p: p.k), field(when=lambda p: p.k):\n        x: uint8",
            "S: is not a with field\\(...\\) block",
        ),
        ("x: list[uint8] = field(count=lambda p: p.k)\n    k: uint8", "x: p.k is not an earlier field"),
        ("k: uint8\n    x: uint8 = field(when=lambda p, *rest: p.k)", "x: is not a lambda of one argument"),
        ("k: uint8\n    with k:\n        x: uint8", "S: is not a with field\\(...\\) block"),
    ],
)
def test_bad_lambda_is_rejected(build_package, body, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + f"class S:\n    {body}\n"})


def test_a_predicate_member_gated_with_its_field_is_accepted(build_package):
    source = HEADER + "class S:\n    k: E\n    x: uint8 = field(when=lambda p: p.k == E.C, since=3)\n"

    assert when_of(build_package({"a": source}), "x") is not None


def test_a_field_named_after_a_keyword_is_read_without_the_underscore(build_package):
    package = build_package(
        {"a": HEADER + "class S:\n    pass_: uint8\n    x: uint8 = field(when=lambda p: p.pass_)\n"}
    )

    assert when_of(package, "x") == FieldRef("pass")


def test_a_predicate_and_a_count_may_read_a_field_gated_like_themselves(build_package):
    source = HEADER + (
        "class S:\n    k: uint8 = field(since=2)\n"
        "    x: uint8 = field(since=2, when=lambda p: p.k)\n"
        "    xs: list[uint8] = field(since=2, count=lambda p: p.k)\n"
    )
    fields = family_of(build_package({"a": source}), "S").declarations[0].fields

    assert fields[1].when == FieldRef("k")
    assert fields[2].type.count == FieldRef("k")


def test_len_counts_a_dict(build_package):
    source = HEADER + ("class S:\n    m: dict[uint8, uint8]\n    xs: list[uint8] = field(count=lambda p: len(p.m))\n")

    assert family_of(build_package({"a": source}), "S").declarations[0].fields[1].type.count == Len("m")


def test_a_lambda_may_default_its_argument(build_package):
    package = build_package({"a": HEADER + "class S:\n    k: uint8\n    x: uint8 = field(when=lambda p=1: p.k)\n"})

    assert when_of(package, "x") == FieldRef("k")
