import pytest

from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    Array,
    CompilerError,
    EnumName,
    EnumRef,
    Int,
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
java_package = "dev.endstone.protocol"
"""


def field_types(package, module=0):
    struct = next(family for family in package.modules[module].families if family.name == "A")
    return [field.type for field in struct.declarations[0].fields]


def test_type_overrides_the_encoding_of_an_integer(build_package):
    package = build_package({"a": HEADER + "class A:\n    x: int16 = field(type=varint32)\n    y: uint8\n"})

    assert field_types(package) == [Primitive("int16", encoded="varint32"), Primitive("uint8")]


def test_type_overrides_the_encoding_of_an_alias(build_package):
    package = build_package({"a": HEADER + "type Id = int64\n\nclass A:\n    x: Id = field(type=uvarint32)\n"})

    assert field_types(package) == [AliasRef(package.modules[0].families[0], encoded="uvarint32")]


def test_type_on_an_enum_picks_its_encoding_or_names_it(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n\n"
        + "class A:\n    x: E = field(type=varint32)\n    y: E = field(type=str)\n    z: E\n"
    )
    package = build_package({"a": source})

    enum = package.modules[0].families[0]

    assert field_types(package) == [EnumRef(enum, encoded="varint32"), EnumName(enum), EnumRef(enum)]


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
        Optional(Primitive("int32", encoded="varint32")),
        List(EnumName(enum), Primitive("uvarint32")),
        List(Optional(Primitive("int16", encoded="varint32")), Primitive("uvarint32")),
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
        Map(StructRef(b), Primitive("int16", encoded="varint32")),
    ]


REENCODE = "type and endian do not reach exactly one scalar that takes them"


@pytest.mark.parametrize(
    "line",
    [
        pytest.param("x: uuid.UUID = field(type=varint32)", id="uuid-integer"),
        pytest.param("x: uuid.UUID = field(type=str)", id="uuid-str"),
        pytest.param("x: uuid.UUID = field(endian='big')", id="uuid-big"),
        pytest.param("x: C = field(type=str)", id="builtin-str"),
    ],
)
def test_a_builtin_takes_no_encoding(build_package, line):
    source = HEADER + "import uuid\nfrom protocol import builtin\n\n@builtin\nclass C:\n    pass\n\n"
    source += "class A:\n    " + line + "\n"

    with pytest.raises(CompilerError, match=REENCODE):
        build_package({"a": source})


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("x: B = field(type=varint32)", REENCODE),
        ("x: str = field(type=str)", REENCODE),
        ("x: bool = field(type=uint8)", REENCODE),
        ("x: int16 = field(type=str)", REENCODE),
        ("x: dict[int16, int16] = field(type=varint32)", REENCODE),
        ("x: dict[B, B] = field(type=varint32)", REENCODE),
        ("x: int16 = field(type=B)", "type is not str or an integer primitive"),
        ("x: int16 = field(type=bool)", "type is not str or an integer primitive"),
        ("x: Id = field(type=str)", REENCODE),
    ],
)
def test_type_must_reach_exactly_one_scalar_that_takes_it(build_package, line, message):
    source = HEADER + "class B:\n    pass\n\ntype Id = int32\n\nclass A:\n    " + line + "\n"

    with pytest.raises(CompilerError, match=message):
        build_package({"a": source})


@pytest.mark.parametrize(
    "encoded",
    [
        "int8",
        "uint8",
        "int16",
        "uint16",
        "int32",
        "uint32",
        "int64",
        "uint64",
        "varint32",
        "varint64",
        "uvarint32",
        "uvarint64",
    ],
)
def test_type_accepts_every_integer_encoding(build_package, encoded):
    package = build_package({"a": HEADER + f"class A:\n    x: int32 = field(type={encoded})\n"})

    assert field_types(package) == [Primitive("int32", encoded=encoded)]


@pytest.mark.parametrize("name", ["int16", "uint16", "int32", "uint32", "int64", "uint64"])
def test_endian_accepts_every_16_32_and_64_bit_integer(build_package, name):
    package = build_package({"a": HEADER + f"class A:\n    x: {name} = field(endian='big')\n"})

    assert field_types(package) == [Primitive(name, endian="big")]


def test_endian_marks_a_fixed_width_integer(build_package):
    source = HEADER + "class E(IntEnum, uint8):\n    A = 1\n\nclass A:\n    x: int32 = field(endian='big')\n"
    source += "    y: E = field(type=int32, endian='big')\n    z: list[int16] = field(endian='big')\n"
    package = build_package({"a": source})

    enum = package.modules[0].families[0]

    assert field_types(package) == [
        Primitive("int32", endian="big"),
        EnumRef(enum, encoded="int32", endian="big"),
        List(Primitive("int16", endian="big"), Primitive("uvarint32")),
    ]


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("x: int32 = field(endian='little')", 'endian is not "big"'),
        ("x: uint8 = field(endian='big')", REENCODE),
        ("x: varint32 = field(endian='big')", REENCODE),
        ("x: int32 = field(type=varint32, endian='big')", REENCODE),
        ("x: str = field(endian='big')", REENCODE),
        ("x: B = field(endian='big')", REENCODE),
        ("x: E = field(endian='big')", REENCODE),
        ("x: E = field(type=str, endian='big')", REENCODE),
        ("x: E = field(type=varint32, endian='big')", REENCODE),
        ("x: Id = field(endian='big')", REENCODE),
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


def test_cereal_false_declares_a_second_flavour_of_the_name(build_package):
    source = HEADER + "class B:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    y: uint16\n"
    package = build_package({"a": source})

    cereal, pre_cereal = package.modules[0].families

    assert (cereal.cereal, pre_cereal.cereal) == (True, False)
    assert [field.name for field in cereal.declarations[0].fields] == ["x"]
    assert [field.name for field in pre_cereal.declarations[0].fields] == ["y"]


def test_field_cereal_false_reaches_the_pre_cereal_family_through_containers(build_package):
    source = (
        HEADER
        + "class B:\n    pass\n\n@type(cereal=False)\nclass B:\n    y: uint16\n\n"
        + "class A:\n    a: B\n    b: B = field(cereal=False)\n    c: list[B] | None = field(cereal=False)\n"
        + "    d: dict[B, B] = field(cereal=False)\n    e: Union[B, None] = field(cereal=False)\n"
        + "    f: array[B, 2] = field(cereal=False)\n"
    )
    package = build_package({"a": source})

    cereal, pre_cereal, _ = package.modules[0].families

    assert field_types(package) == [
        StructRef(cereal),
        StructRef(pre_cereal),
        Optional(List(StructRef(pre_cereal), Primitive("uvarint32"))),
        Map(StructRef(pre_cereal), StructRef(pre_cereal)),
        Variant((StructRef(pre_cereal), None)),
        Array(StructRef(pre_cereal), 2),
    ]


def test_cereal_false_enum_name_codes_through_type(build_package):
    source = (
        HEADER
        + "class E(IntEnum, uint8):\n    A = 1\n\n@type(cereal=False)\nclass E(IntEnum, uint8):\n    A = 1\n\n"
        + "class A:\n    x: E = field(type=str, cereal=False)\n"
    )
    package = build_package({"a": source})

    pre_cereal = package.modules[0].families[1]

    assert field_types(package) == [EnumName(pre_cereal)]


def test_cereal_false_family_imports_by_its_cereal_name(build_package):
    modules = {
        "a": HEADER + "class B:\n    pass\n\n@type(cereal=False)\nclass B:\n    y: uint8\n",
        "b": HEADER + "from protocol.a import B\n\nclass A:\n    x: B = field(cereal=False)\n",
    }
    package = build_package(modules)

    pre_cereal = package.modules[0].families[1]

    assert field_types(package, 1) == [StructRef(pre_cereal)]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("class B:\n    pass\n\nclass A:\n    x: B = field(cereal=False)\n", "B: has no cereal=False declaration"),
        ("@type(cereal=False)\nclass B:\n    pass\n", "B: a cereal=False declaration needs a cereal one"),
        (
            "class B:\n    pass\n\n" + "@type(cereal=False)\nclass B:\n    pass\n\n" * 2,
            "B: is declared again after an open",
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


def test_a_class_nested_in_a_pre_cereal_owner_is_pre_cereal(build_package):
    source = HEADER + "class B:\n    pass\n\n@type(cereal=False)\nclass B:\n    class C:\n        pass\n"
    package = build_package({"a": source})

    cereal, pre_cereal = package.modules[0].families

    assert [family.cereal for family in pre_cereal.nested] == [False]
    assert cereal.nested == []
    assert [family.name for family in package.modules[0].families] == ["B", "B"]


def test_a_pre_cereal_family_declared_before_its_cereal_sibling_is_reached(build_package):
    source = (
        HEADER
        + "@type(cereal=False)\nclass B:\n    y: uint16\n\nclass B:\n    x: uint8\n\n"
        + "class A:\n    a: B = field(cereal=False)\n"
    )
    package = build_package({"a": source})

    pre_cereal, cereal, _ = package.modules[0].families

    assert (cereal.cereal, pre_cereal.cereal) == (True, False)
    assert field_types(package) == [StructRef(pre_cereal)]


def test_duplicate_counts_the_copies_of_a_field(build_package):
    package = build_package({"a": HEADER + "class A:\n    x: uint8 = field(duplicate=2)\n    y: uint8\n"})

    struct = next(family for family in package.modules[0].families if family.name == "A")

    assert [field.duplicate for field in struct.declarations[0].fields] == [Int(2), None]


@pytest.mark.parametrize(
    ("duplicate", "message"),
    [
        pytest.param('"2"', "x: is not a literal int", id="not_an_int"),
        pytest.param("copies", "x: is not a literal int", id="not_a_literal"),
        pytest.param("True", "x: is not a literal int", id="bool"),
        pytest.param("1", "x: duplicate is fewer than two copies", id="one"),
        pytest.param("0", "x: duplicate is fewer than two copies", id="zero"),
    ],
)
def test_duplicate_is_rejected(build_package, duplicate, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + f"class A:\n    x: uint8 = field(duplicate={duplicate})\n"})


def test_duplicate_is_rejected_on_a_with_block(build_package):
    source = HEADER + "class A:\n    with field(duplicate=2):\n        x: uint8\n"

    with pytest.raises(CompilerError, match="a with block takes only"):
        build_package({"a": source})


INFO = "class Info:\n    id: uint8\n    capable: bool\n\n"


def test_exclude_marks_the_member_at_its_call_site_only(build_package):
    package = build_package({"a": HEADER + INFO + 'class A:\n    x: Info = field(exclude="capable")\n    y: Info\n'})

    info = package.modules[0].families[0]

    assert field_types(package) == [StructRef(info, excluded="capable"), StructRef(info)]


@pytest.mark.parametrize(
    ("annotation", "container"),
    [
        pytest.param("list[Info]", lambda element: List(element, Primitive("uvarint32")), id="list"),
        pytest.param("array[Info, 2]", lambda element: Array(element, 2), id="array"),
        pytest.param("Info | None", Optional, id="optional"),
    ],
)
def test_exclude_marks_the_member_on_the_element_struct(build_package, annotation, container):
    package = build_package({"a": HEADER + INFO + f'class A:\n    x: {annotation} = field(exclude="capable")\n'})

    info = package.modules[0].families[0]

    assert field_types(package) == [container(StructRef(info, excluded="capable"))]


@pytest.mark.parametrize(
    ("exclude", "message"),
    [
        pytest.param("1", "x: is not a literal str", id="not_a_str"),
        pytest.param('["capable"]', "x: is not a literal str", id="a_list"),
        pytest.param("capable", "x: is not a literal str", id="not_a_literal"),
        pytest.param('""', "x: is an empty string", id="empty"),
    ],
)
def test_exclude_is_rejected_unless_one_string_literal(build_package, exclude, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + INFO + f"class A:\n    x: Info = field(exclude={exclude})\n"})


def test_exclude_is_rejected_for_a_member_the_type_does_not_declare(build_package):
    source = HEADER + INFO + 'class A:\n    x: Info = field(exclude="missing")\n'

    with pytest.raises(CompilerError, match=r"A\.x: exclude names missing, which Info does not declare"):
        build_package({"a": source})


def test_exclude_is_rejected_for_a_member_the_type_encodes_only_outside_the_field(build_package):
    source = (
        HEADER
        + "class Info:\n    id: uint8\n    capable: bool = field(since=3)\n\n"
        + 'class A:\n    x: Info = field(until=3, exclude="capable")\n'
    )

    with pytest.raises(
        CompilerError, match=r"A\.x: exclude names capable, which Info does not encode at any protocol the field spans"
    ):
        build_package({"a": source})


def test_exclude_is_rejected_for_a_constant(build_package):
    source = (
        HEADER
        + "from typing import Literal\n"
        + "class Info:\n    _true: Literal[True]\n    capable: bool\n\n"
        + 'class A:\n    x: Info = field(exclude="_true")\n'
    )

    with pytest.raises(CompilerError, match=r"A\.x: exclude names _true, which Info holds as a constant"):
        build_package({"a": source})


@pytest.mark.parametrize(
    "reader",
    [
        pytest.param("extra: uint8 = field(when=lambda p: p.capable != 0)", id="when"),
        pytest.param("extra: list[uint8] = field(count=lambda p: p.capable)", id="count"),
        pytest.param("extra: uint8 = field(duplicate=lambda p: p.capable)", id="duplicate"),
    ],
)
def test_exclude_is_rejected_for_a_member_another_member_reads(build_package, reader):
    source = (
        HEADER
        + f"class Info:\n    id: uint8\n    capable: uint8\n    {reader}\n\n"
        + 'class A:\n    x: Info = field(exclude="capable")\n'
    )

    with pytest.raises(CompilerError, match=r"A\.x: exclude names capable, which Info\.extra reads"):
        build_package({"a": source})


def test_exclude_names_a_keyword_member_without_its_trailing_underscore(build_package):
    source = (
        HEADER
        + "class Info:\n    pass_: uint8\n    extra: uint8 = field(when=lambda p: p.pass_ != 0)\n\n"
        + 'class A:\n    x: Info = field(exclude="pass_")\n'
    )

    with pytest.raises(CompilerError, match=r"A\.x: exclude names pass, which Info\.extra reads"):
        build_package({"a": source})


def test_exclude_is_rejected_on_a_with_block(build_package):
    source = HEADER + INFO + 'class A:\n    with field(exclude="capable"):\n        x: Info\n'

    with pytest.raises(CompilerError, match="a with block takes only"):
        build_package({"a": source})


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param("uint8", id="primitive"),
        pytest.param("dict[uint8, Info]", id="map"),
        pytest.param("Info | uint8", id="union"),
        pytest.param("list[list[Info]]", id="nested_list"),
    ],
)
def test_exclude_is_rejected_on_a_field_that_holds_no_struct(build_package, annotation):
    with pytest.raises(
        CompilerError, match="x: exclude is given to something other than a struct or a list, array or optional of one"
    ):
        build_package({"a": HEADER + INFO + f'class A:\n    x: {annotation} = field(exclude="capable")\n'})
