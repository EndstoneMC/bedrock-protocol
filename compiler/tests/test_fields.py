import pytest

from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    CompilerError,
    EnumName,
    EnumRef,
    List,
    Map,
    Optional,
    Primitive,
    StructRef,
)

HEADER = """
from enum import IntEnum
from protocol import field, int8, int16, int32, int64, packet, type, uint8, uint16, uint32, uvarint32, varint32
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


@pytest.mark.parametrize(
    "line",
    [
        "x: B = field(type=varint32)",
        "x: str = field(type=str)",
        "x: bool = field(type=uint8)",
        "x: int16 = field(type=str)",
        "x: dict[int16, int16] = field(type=varint32)",
        "x: dict[B, B] = field(type=varint32)",
        "x: int16 = field(type=B)",
        "x: int16 = field(type=bool)",
    ],
)
def test_type_must_reach_exactly_one_scalar_that_takes_it(build_package, line):
    with pytest.raises(CompilerError):
        build_package({"a": HEADER + "class B:\n    pass\n\nclass A:\n    " + line + "\n"})


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
    "line",
    [
        "x: int32 = field(endian='little')",
        "x: uint8 = field(endian='big')",
        "x: varint32 = field(endian='big')",
        "x: int32 = field(type=varint32, endian='big')",
        "x: str = field(endian='big')",
        "x: B = field(endian='big')",
        "x: E = field(endian='big')",
        "x: E = field(type=str, endian='big')",
    ],
)
def test_endian_is_big_and_on_a_fixed_width_integer_only(build_package, line):
    source = HEADER + "class B:\n    pass\n\nclass E(IntEnum, uint8):\n    A = 1\n\nclass A:\n    " + line + "\n"

    with pytest.raises(CompilerError):
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
        + "    d: dict[B, B] = field(cereal=False)\n"
    )
    package = build_package({"a": source})

    cereal, _, legacy = package.modules[0].families

    assert field_types(package) == [
        StructRef(cereal),
        StructRef(legacy),
        Optional(List(StructRef(legacy), Primitive("uvarint32"))),
        Map(StructRef(legacy), StructRef(legacy)),
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
    ],
)
def test_cereal_is_rejected(build_package, source, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + source})
