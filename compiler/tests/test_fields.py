import pytest

from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    Array,
    CompilerError,
    EnumName,
    EnumRef,
    List,
    Map,
    Optional,
    Primitive,
    StructRef,
    Variant,
)

HEADER = """
from enum import IntEnum
from protocol import (
    array, field, int8, int16, int32, int64, packet, type, uint8, uint16, uint32, uint64, uvarint32, uvarint64,
    varint32, varint64
)
from typing import Union
package = "bedrock.protocol"
"""


def field_types(package, module=0):
    struct = next(family for family in package.modules[module].families if family.name == "A")
    return [field.type for field in struct.declarations[0].fields]


def test_type_overrides_the_wire_of_an_integer(build_package):
    package = build_package({"a": HEADER + "class A:\n    x: int16 = field(type=varint32)\n    y: uint8\n"})

    assert field_types(package) == [Primitive("int16", wire="varint32"), Primitive("uint8")]


def test_type_overrides_the_wire_of_an_alias(build_package):
    package = build_package({"a": HEADER + "type Id = int64\n\nclass A:\n    x: Id = field(type=uvarint32)\n"})

    assert field_types(package) == [AliasRef(package.modules[0].families[0], wire="uvarint32")]


def test_type_on_an_enum_picks_its_wire_or_names_it(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n\n"
        + "class A:\n    x: E = field(type=varint32)\n    y: E = field(type=str)\n    z: E\n"
    )
    package = build_package({"a": source})

    enum = package.modules[0].families[0]

    assert field_types(package) == [EnumRef(enum, wire="varint32"), EnumName(enum), EnumRef(enum)]


def test_type_reaches_through_optional_and_list(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n\n"
        + "class A:\n    x: int32 | None = field(type=varint32)\n"
        + "    y: list[E] = field(type=str)\n    z: list[int16 | None] = field(type=varint32)\n"
    )
    package = build_package({"a": source})

    enum = package.modules[0].families[0]

    assert field_types(package) == [
        Optional(Primitive("int32", wire="varint32")),
        List(EnumName(enum), Primitive("uvarint32")),
        List(Optional(Primitive("int16", wire="varint32")), Primitive("uvarint32")),
    ]


def test_type_on_a_dict_reaches_its_one_scalar_half(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n\nclass B:\n    pass\n\n"
        + "class A:\n    x: dict[E, B] = field(type=str)\n    y: dict[B, int16] = field(type=varint32)\n"
    )
    package = build_package({"a": source})

    enum, b = package.modules[0].families[:2]

    assert field_types(package) == [
        Map(EnumName(enum), StructRef(b)),
        Map(StructRef(b), Primitive("int16", wire="varint32")),
    ]


REWIRE = "type and endian do not reach exactly one scalar that takes them"


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("x: B = field(type=varint32)", REWIRE),
        ("x: str = field(type=str)", REWIRE),
        ("x: bool = field(type=uint8)", REWIRE),
        ("x: int16 = field(type=str)", REWIRE),
        ("x: dict[int16, int16] = field(type=varint32)", REWIRE),
        ("x: dict[B, B] = field(type=varint32)", REWIRE),
        ("x: int16 = field(type=B)", "type is not str or an integer primitive"),
        ("x: int16 = field(type=bool)", "type is not str or an integer primitive"),
        ("x: Id = field(type=str)", REWIRE),
        ("x: Name = field(type=uint8)", REWIRE),
    ],
)
def test_type_must_reach_exactly_one_scalar_that_takes_it(build_package, line, message):
    source = HEADER + "class B:\n    pass\n\ntype Id = int32\ntype Name = str\n\nclass A:\n    " + line + "\n"

    with pytest.raises(CompilerError, match=message):
        build_package({"a": source})


@pytest.mark.parametrize("wire", ["int8", "uint8", "int16", "uint16", "int32", "uint32", "int64", "uint64"])
@pytest.mark.parametrize("wire_type", ["varint32", "varint64", "uvarint32", "uvarint64"])
def test_type_accepts_every_integer_wire(build_package, wire, wire_type):
    package = build_package(
        {"a": HEADER + f"class A:\n    x: int32 = field(type={wire})\n    y: uint8 = field(type={wire_type})\n"}
    )

    assert field_types(package) == [Primitive("int32", wire=wire), Primitive("uint8", wire=wire_type)]


@pytest.mark.parametrize("name", ["int16", "uint16", "int32", "uint32", "int64", "uint64"])
def test_endian_accepts_every_fixed_width_integer(build_package, name):
    package = build_package({"a": HEADER + f"class A:\n    x: {name} = field(endian='big')\n"})

    assert field_types(package) == [Primitive(name, endian="big")]


def test_endian_marks_a_fixed_width_integer(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    A = 1\n\nclass A:\n    x: int32 = field(endian='big')\n"
    source += "    y: E = field(type=int32, endian='big')\n    z: list[int16] = field(endian='big')\n"
    package = build_package({"a": source})

    enum = package.modules[0].families[0]

    assert field_types(package) == [
        Primitive("int32", endian="big"),
        EnumRef(enum, wire="int32", endian="big"),
        List(Primitive("int16", endian="big"), Primitive("uvarint32")),
    ]


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("x: int32 = field(endian='little')", 'endian is not "big"'),
        ("x: uint8 = field(endian='big')", REWIRE),
        ("x: varint32 = field(endian='big')", REWIRE),
        ("x: int32 = field(type=varint32, endian='big')", REWIRE),
        ("x: str = field(endian='big')", REWIRE),
        ("x: B = field(endian='big')", REWIRE),
        ("x: E = field(endian='big')", REWIRE),
        ("x: E = field(type=str, endian='big')", REWIRE),
        ("x: E = field(type=varint32, endian='big')", REWIRE),
        ("x: Id = field(endian='big')", REWIRE),
    ],
)
def test_endian_is_big_and_on_a_fixed_width_integer_only(build_package, line, message):
    source = (
        HEADER
        + "class B:\n    pass\n\nclass E(IntEnum, uint8):\n    A = 1\n\ntype Id = int32\n\nclass A:\n    "
        + line
        + "\n"
    )

    with pytest.raises(CompilerError, match=message):
        build_package({"a": source})


def test_enum_without_an_underlying_type_takes_type(build_package):
    source = (
        HEADER
        + "class E(IntEnum):\n    A = 1\n\n"
        + "class A:\n    x: E = field(type=uint8)\n    y: E = field(type=str)\n    z: E\n"
    )
    package = build_package({"a": source})

    enum = package.modules[0].families[0]

    assert field_types(package) == [EnumRef(enum, wire="uint8"), EnumName(enum), EnumRef(enum)]


def test_cereal_false_declares_a_second_flavour_of_the_name(build_package):
    source = HEADER + "class B:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    y: uint16\n"
    package = build_package({"a": source})

    cereal, legacy = package.modules[0].families

    assert (cereal.cereal, legacy.cereal) == (True, False)
    assert [field.name for field in cereal.declarations[0].fields] == ["x"]
    assert [field.name for field in legacy.declarations[0].fields] == ["y"]


def test_field_cereal_false_reaches_the_legacy_family_through_containers(build_package):
    source = (
        HEADER
        + "class B:\n    pass\n\n@type(cereal=False)\nclass B:\n    y: uint16\n\n"
        + "class A:\n    a: B\n    b: B = field(cereal=False)\n    c: list[B] | None = field(cereal=False)\n"
        + "    d: dict[B, B] = field(cereal=False)\n    e: Union[B, None] = field(cereal=False)\n"
        + "    f: array[B, 2] = field(cereal=False)\n"
    )
    package = build_package({"a": source})

    cereal, _, legacy = package.modules[0].families

    assert field_types(package) == [
        StructRef(cereal),
        StructRef(legacy),
        Optional(List(StructRef(legacy), Primitive("uvarint32"))),
        Map(StructRef(legacy), StructRef(legacy)),
        Variant((StructRef(legacy), None)),
        Array(StructRef(legacy), 2),
    ]


def test_cereal_false_enum_name_codes_through_type(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n\n@type(cereal=False)\nclass E(IntEnum, uint8):\n    A = 1\n\n"
        + "class A:\n    x: E = field(type=str, cereal=False)\n"
    )
    package = build_package({"a": source})

    legacy = package.modules[0].families[-1]

    assert field_types(package) == [EnumName(legacy)]


def test_cereal_false_family_imports_by_its_cereal_name(build_package):
    modules = {
        "a": HEADER + "class B:\n    pass\n\n@type(cereal=False)\nclass B:\n    y: uint8\n",
        "b": HEADER + "from protocol.a import B\n\nclass A:\n    x: B = field(cereal=False)\n",
    }
    package = build_package(modules)

    legacy = package.modules[0].families[1]

    assert field_types(package, 1) == [StructRef(legacy)]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("class B:\n    pass\n\nclass A:\n    x: B = field(cereal=False)\n", "B: has no cereal=False declaration"),
        ("@type(cereal=False)\nclass B:\n    pass\n", "B: a cereal=False declaration needs a cereal one"),
        (
            "class B:\n    pass\n\n" + "@type(cereal=False)\nclass B:\n    pass\n\n" * 2,
            "B: is already declared",
        ),
        ("class A:\n    @type(cereal=False)\n    class B:\n        pass\n", "B: cereal=False marks a module-scope"),
        (
            "class B:\n    pass\n\n@packet(id=1, cereal=False)\nclass A:\n    pass\n",
            "unexpected keyword argument 'cereal'",
        ),
        ("class A:\n    x: uint8 = field(cereal=1)\n", "x: is not a literal bool"),
        ("@type(cereal=0)\nclass B:\n    pass\n", "type: is not a literal bool"),
        (
            "class B:\n    pass\n\n@type(cereal=False)\nclass B(IntEnum, uint8):\n    A = 1\n",
            "a.py:[0-9]+:[0-9]+: B: a cereal=False declaration needs a cereal one",
        ),
        ("class A:\n    x: uint8 = field(cereal=False)\n", "uint8: has no cereal=False declaration"),
        ("class A:\n    x: uuid.UUID = field(cereal=False)\n", "has no cereal=False declaration"),
        (
            "class B:\n    pass\n\n@type(cereal=False)\nclass B:\n    pass\n\n"
            + "type U = B | uint8\n\nclass A:\n    x: U = field(cereal=False)\n",
            "U: has no cereal=False declaration",
        ),
        ("class A:\n    x: Literal[True] = field(cereal=False)\n", "x: has no cereal=False declaration"),
    ],
)
def test_cereal_is_rejected(build_package, source, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + "import uuid\nfrom typing import Literal\n" + source})


def test_a_class_nested_in_a_legacy_owner_is_legacy(build_package):
    source = HEADER + "class B:\n    pass\n\n@type(cereal=False)\nclass B:\n    class C:\n        pass\n"
    package = build_package({"a": source})

    cereal, legacy = package.modules[0].families

    assert [family.cereal for family in legacy.nested] == [False]
    assert cereal.nested == []
    assert [family.name for family in package.modules[0].families] == ["B", "B"]


def test_a_legacy_declared_before_its_cereal_sibling_is_reached(build_package):
    source = (
        HEADER
        + "@type(cereal=False)\nclass B:\n    y: uint16\n\nclass B:\n    x: uint8\n\n"
        + "class A:\n    a: B = field(cereal=False)\n"
    )
    package = build_package({"a": source})

    cereal, _, legacy = package.modules[0].families

    assert (cereal.cereal, legacy.cereal) == (True, False)
    assert field_types(package) == [StructRef(legacy)]
