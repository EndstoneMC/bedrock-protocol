import pytest

from bedrock_protocol_compiler.builder import UUID
from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    Array,
    Bitset,
    BuiltinRef,
    CompilerError,
    List,
    Literal,
    Map,
    MemberRef,
    Optional,
    Primitive,
    StructRef,
    Variant,
)

HEADER = """
from enum import IntEnum
from typing import Literal, Union
from protocol import array, bitset, field, int8, int32, uint8, uint16, uint32, uvarint32, varint32
package = "bedrock.protocol"
"""


uvarint32 = Primitive("uvarint32")


def field_types(package):
    return [field.type for field in package.modules[0].families[-1].declarations[0].fields]


def test_optional_wraps_one_type_and_none(build_package):
    package = build_package({"a": HEADER + "class B:\n    pass\n\nclass A:\n    x: uint8 | None\n    y: B | None\n"})

    b = package.modules[0].families[0]

    assert field_types(package) == [Optional(Primitive("uint8")), Optional(StructRef(b))]


def test_union_keeps_declaration_order_and_none_position(build_package):
    package = build_package(
        {"a": HEADER + "class B:\n    pass\n\nclass A:\n    x: uint8 | B | None\n    y: None | uint8 | B\n"}
    )

    b = package.modules[0].families[0]
    uint8 = Primitive("uint8")

    assert field_types(package) == [
        Variant((uint8, StructRef(b), None)),
        Variant((None, uint8, StructRef(b))),
    ]


def test_typing_union_is_a_variant_even_with_none(build_package):
    package = build_package({"a": HEADER + "class A:\n    x: Union[uint8, None]\n    y: Union[uint8, uint16, None]\n"})

    assert field_types(package) == [
        Variant((Primitive("uint8"), None)),
        Variant((Primitive("uint8"), Primitive("uint16"), None)),
    ]


def test_union_alias_resolves_to_its_variant_at_every_use(build_package):
    source = (
        HEADER + "class B:\n    pass\n\nclass C:\n    pass\n\ntype V = B | C\n\nclass A:\n    x: V\n    y: V | None\n"
    )
    package = build_package({"a": source})

    b, c = package.modules[0].families[:2]
    variant = Variant((StructRef(b), StructRef(c)))

    assert field_types(package) == [variant, Optional(variant)]


def test_union_alias_is_not_flattened_into_an_enclosing_union(build_package):
    source = HEADER + "type V = uint8 | uint16\n\nclass A:\n    x: V | uint32\n"
    package = build_package({"a": source})

    assert field_types(package) == [Variant((Variant((Primitive("uint8"), Primitive("uint16"))), Primitive("uint32")))]


def test_union_alias_naming_a_later_union_alias_builds_the_nested_variant(build_package):
    source = HEADER + "type V = W | uint8\n\ntype W = uint16 | uint32\n\nclass A:\n    x: V\n"
    package = build_package({"a": source})

    inner = Variant((Primitive("uint16"), Primitive("uint32")))

    assert field_types(package) == [Variant((inner, Primitive("uint8")))]


def test_union_alias_naming_a_later_primitive_alias_builds(build_package):
    source = HEADER + "type V = Id | uint8\n\ntype Id = uint32\n\nclass A:\n    x: V\n"
    package = build_package({"a": source})

    id_alias = package.modules[0].families[0]

    assert field_types(package) == [Variant((AliasRef(id_alias), Primitive("uint8")))]


def test_union_alias_naming_an_alias_from_a_later_module_builds(build_package):
    imports = "from bedrock_protocol_compiler.dsl import uint8, uint32\npackage = 'bedrock.protocol'\n"
    a = imports + "from protocol.b import Id\n\ntype V = Id | uint8\n"
    b = imports + "type Id = uint32\n"
    package = build_package({"a": a, "b": b})

    assert package.modules[0].families == ()


def test_union_alias_naming_itself_is_rejected(build_package):
    with pytest.raises(CompilerError, match="V: names itself"):
        build_package({"a": HEADER + "type V = V | uint8\n"})


def test_union_aliases_naming_each_other_are_rejected(build_package):
    with pytest.raises(CompilerError, match="names itself"):
        build_package({"a": HEADER + "type V = W | uint8\n\ntype W = V | uint16\n"})


def test_union_alias_imported_by_another_module_resolves_to_its_variant(build_package):
    imports = "from bedrock_protocol_compiler.dsl import uint8, uint16\npackage = 'bedrock.protocol'\n"
    a = imports + "type V = uint8 | uint16\n"
    b = imports + "from protocol.a import V\n\nclass B:\n    x: V\n"
    package = build_package({"a": a, "b": b})

    assert package.modules[1].families[0].declarations[0].fields[0].type == Variant(
        (Primitive("uint8"), Primitive("uint16"))
    )


def test_union_alias_is_not_a_family(build_package):
    package = build_package({"a": HEADER + "type V = uint8 | uint16\n\ntype Id = uint32\n"})

    assert [family.name for family in package.modules[0].families] == ["Id"]


def test_union_alias_may_name_an_enum_member_width(build_package):
    source = HEADER + "type V = bitset[E.M] | uint8\n\nclass E(IntEnum, uint8):\n    M = 1\n\nclass A:\n    x: V\n"
    package = build_package({"a": source})

    e = package.modules[0].families[0]

    assert field_types(package) == [Variant((Bitset(MemberRef(e, "M")), Primitive("uint8")))]


def test_none_first_two_case_union_is_a_variant(build_package):
    package = build_package({"a": HEADER + "class A:\n    x: None | uint8\n"})

    assert field_types(package) == [Variant((None, Primitive("uint8")))]


def test_long_pipe_chain_is_one_flat_variant(build_package):
    package = build_package({"a": HEADER + "class B:\n    pass\n\nclass A:\n    x: uint8 | uint16 | uint32 | B\n"})

    b = package.modules[0].families[0]

    assert field_types(package) == [
        Variant((Primitive("uint8"), Primitive("uint16"), Primitive("uint32"), StructRef(b)))
    ]


def test_list_count_is_uvarint32_by_default(build_package):
    package = build_package(
        {"a": HEADER + "class A:\n    x: list[uint8]\n    y: list[list[str]]\n    z: list[uint8] | None\n"}
    )

    assert field_types(package) == [
        List(Primitive("uint8"), uvarint32),
        List(List(Primitive("str"), uvarint32), uvarint32),
        Optional(List(Primitive("uint8"), uvarint32)),
    ]


@pytest.mark.parametrize("prefix", ["uint32", "uint16", "varint32"])
def test_list_prefix_is_the_named_primitive(build_package, prefix):
    package = build_package({"a": HEADER + f"class A:\n    x: list[uint8] = field(prefix={prefix})\n"})

    assert field_types(package) == [List(Primitive("uint8"), Primitive(prefix))]


def test_list_prefix_reaches_only_the_fields_own_list(build_package):
    package = build_package({"a": HEADER + "class A:\n    x: list[list[uint8]] = field(prefix=uint32)\n"})

    assert field_types(package) == [List(List(Primitive("uint8"), uvarint32), Primitive("uint32"))]


def test_dict_holds_key_and_value(build_package):
    package = build_package({"a": HEADER + "class A:\n    x: dict[str, int32]\n    y: dict[float, list[uint8]]\n"})

    assert field_types(package) == [
        Map(Primitive("str"), Primitive("int32")),
        Map(Primitive("float"), List(Primitive("uint8"), uvarint32)),
    ]


def test_array_holds_element_and_size_and_nests(build_package):
    package = build_package(
        {"a": HEADER + "class A:\n    x: array[float, 3]\n    y: array[array[int8, 16], 4] | None\n"}
    )

    assert field_types(package) == [
        Array(Primitive("float"), 3),
        Optional(Array(Array(Primitive("int8"), 16), 4)),
    ]


def test_container_reaches_a_uuid(build_package):
    package = build_package({"a": HEADER + "import uuid\n\nclass A:\n    x: list[uuid.UUID]\n"})

    assert field_types(package) == [List(BuiltinRef(UUID), uvarint32)]


def test_literal_holds_a_bool_a_string_or_an_enum_member(build_package):
    source = HEADER + (
        "class E(IntEnum, uint8):\n    M = 1\n\n"
        "class A:\n    x: Literal[True] = field()\n    y: Literal[False]\n    z: Literal['raw']\n    w: Literal[E.M]\n"
    )
    package = build_package({"a": source})

    e = package.modules[0].families[0]

    assert field_types(package) == [Literal(True), Literal(False), Literal("raw"), Literal(MemberRef(e, "M"))]


def test_literal_reaches_an_enum_nested_in_an_owner(build_package):
    source = HEADER + (
        "class Owner:\n    class E(IntEnum, uint8):\n        M = 1\n\nclass A:\n    x: Literal[Owner.E.M]\n"
    )
    package = build_package({"a": source})

    owner = package.modules[0].families[0]

    assert field_types(package) == [Literal(MemberRef(owner.nested[0], "M"))]


def test_bitset_is_as_wide_as_an_enum_member(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    COUNT = 3\n\nclass A:\n    x: bitset[E.COUNT]\n"
    package = build_package({"a": source})

    e = package.modules[0].families[0]

    assert field_types(package) == [Bitset(MemberRef(e, "COUNT"))]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("class A:\n    x: list\n", "list: is not a type"),
        ("class A:\n    x: list[uint8, uint8]\n", r"list\[uint8, uint8\]: is not a type with these arguments"),
        ("class A:\n    x: dict[uint8]\n", r"dict\[uint8\]: is not a type with these arguments"),
        ("class A:\n    x: array[uint8]\n", r"array\[uint8\]: is not a type with these arguments"),
        ("class A:\n    x: array[uint8, 'a']\n", "array: is not a literal int"),
        ("class A:\n    x: array[uint8, True]\n", "array: is not a literal int"),
        ("class A:\n    x: array\n", "array: is not a type"),
        ("class A:\n    x: Union[uint8, uint16, None, 3]\n", "3: is not a type"),
        ("class A:\n    x: Literal[1]\n", "1: is not an enum member"),
        ("class A:\n    x: Literal[None]\n", "None: is not an enum member"),
        ("class A:\n    x: Literal['a', 'b']\n", "is not a type with these arguments"),
        ("class A:\n    x: Literal[uint8.M]\n", r"uint8\.M: is not an enum member"),
        ("class A:\n    x: bitset[3]\n", "3: is not an enum member"),
        ("class A:\n    x: Missing[uint8]\n", "Missing: is not defined"),
        ("class A:\n    x: list[Missing]\n", "Missing: is not defined"),
        ("class A:\n    x: uint8 | Missing\n", "Missing: is not defined"),
        ("class A:\n    x: uint8 | 'B'\n", "string annotations are not allowed"),
        ("class A:\n    x: uint8 = field(prefix=uint32)\n", "x: prefix is given to something other than a list"),
        ("class A:\n    x: list[uint8] | None = field(prefix=uint32)\n", "x: prefix is given to something other"),
        ("class A:\n    x: dict[str, str] = field(prefix=uint32)\n", "x: prefix is given to something other"),
        ("class A:\n    x: list[uint8] = field(prefix=uint8)\n", "x: prefix is not uint32, uint16 or varint32"),
        ("class A:\n    x: list[uint8] = field(prefix=uvarint32)\n", "x: prefix is not uint32, uint16 or varint32"),
        ("class A:\n    x: list[uint8] = field(prefix=str)\n", "x: prefix is not uint32, uint16 or varint32"),
        ("class A:\n    x: list[uint8] = field(prefix=Missing)\n", "Missing: is not defined"),
        ("type X = list[uint8]\n", "X: is not a union"),
        ("type X = uint8 | None\n", "X: is not a union"),
        ("class A:\n    x: list[Literal[True]]\n", "is not a type with these arguments"),
        ("class A:\n    x: Literal['a'] | None\n", "is not a type with these arguments"),
        ("class A:\n    x: Literal[True] | uint8\n", "is not a type with these arguments"),
        ("class A:\n    x: dict[str, Literal[True]]\n", "is not a type with these arguments"),
        ("class A:\n    x: Union[uint8]\n", "is not a type with these arguments"),
    ],
)
def test_container_is_rejected(build_package, source, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + source})


def test_literal_naming_an_absent_member_is_rejected(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    M = 1\n\nclass A:\n    x: Literal[E.N]\n"

    with pytest.raises(CompilerError, match=r"E\.N: is not an enum member"):
        build_package({"a": source})
