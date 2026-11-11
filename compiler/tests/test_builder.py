import pytest

from bedrock_protocol_compiler.builder import build
from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    BuiltinRef,
    CompilerError,
    Primitive,
    StructRef,
)

HEADER = """
from protocol import builtin, field, packet, type, uint8, uint32, double
package = "bedrock.protocol"
"""


def test_package_lists_versions_and_modules(build_package):
    package = build_package({"a": 'package = "a.b"\n', "b": 'package = "a.b"\n'}, "versions = (1, 2, 3)\n")

    assert package.versions == (1, 2, 3)
    assert [(module.stem, module.package) for module in package.modules] == [("a", "a.b"), ("b", "a.b")]


def test_modules_declare_one_package(build_package):
    with pytest.raises(CompilerError, match=r"b\.py: package: differs from a\.py's"):
        build_package({"a": 'package = "a.b"\n', "b": 'package = "a.c"\n'})


def test_docstrings_declare_nothing(build_package):
    package = build_package(
        {"a": '"""Module."""\n' + HEADER + 'class A:\n    """Struct."""\n    x: uint8\n'},
        '"""Init."""\n'
        "from bedrock_protocol_compiler.dsl import builtin, double, field, packet, type, uint8, uint32\n"
        "versions = (1, 2, 3)\n",
    )

    assert [field.name for field in package.modules[0].families[0].declarations[0].fields] == ["x"]


def test_struct_fields_keep_declaration_order(build_package):
    package = build_package(
        {"a": HEADER + "class A:\n    x: uint8\n    y: double\n    z: str\n    w: bytes\n    v: bool\n    u: float\n"}
    )

    struct = package.modules[0].families[0]

    assert [(field.name, field.type) for field in struct.declarations[0].fields] == [
        ("x", Primitive("uint8")),
        ("y", Primitive("double")),
        ("z", Primitive("str")),
        ("w", Primitive("bytes")),
        ("v", Primitive("bool")),
        ("u", Primitive("float")),
    ]


def test_field_named_after_a_keyword_drops_its_trailing_underscore(build_package):
    package = build_package({"a": HEADER + "class A:\n    pass_: uint8\n    other_: uint8\n"})

    fields = package.modules[0].families[0].declarations[0].fields

    assert [field.name for field in fields] == ["pass", "other_"]


def test_packet_carries_its_id(build_package):
    package = build_package({"a": HEADER + "@packet(id=7)\nclass A:\n    pass\n\n@type()\nclass B:\n    pass\n"})

    assert [family.packet_id for family in package.modules[0].families] == [7, None]


def test_type_alias_names_a_primitive(build_package):
    package = build_package({"a": HEADER + "type Id = uint32\n\nclass A:\n    id: Id\n"})

    alias, struct = package.modules[0].families

    assert alias.primitive == Primitive("uint32")
    assert struct.declarations[0].fields[0].type == AliasRef(alias)


def test_builtin_is_referenced_by_name(build_package):
    package = build_package({"a": HEADER + "@builtin\nclass Tag:\n    '''A tag.'''\n\nclass A:\n    tag: Tag\n"})

    tag, struct = package.modules[0].families

    assert (tag.name, tag.stem) == ("Tag", "a")
    assert struct.declarations[0].fields[0].type == BuiltinRef(tag)


def test_uuid_is_a_builtin(build_package):
    package = build_package({"a": HEADER + "import uuid\n\nclass A:\n    uuid: uuid.UUID\n"})

    field_type = package.modules[0].families[0].declarations[0].fields[0].type

    assert (field_type.builtin.name, field_type.builtin.stem) == ("UUID", "uuid")


def test_families_record_their_module(build_package):
    package = build_package({"a": HEADER + "type Id = uint8\n\nclass A:\n    class B:\n        pass\n"})

    alias, a = package.modules[0].families

    assert [alias.module, a.module, a.nested[0].module] == ["a", "a", "a"]


def test_forward_reference_resolves(build_package):
    package = build_package({"a": HEADER + "class A:\n    b: B\n\nclass B:\n    pass\n"})

    a, b = package.modules[0].families

    assert a.declarations[0].fields[0].type == StructRef(b)


def test_nested_struct_resolves_bare_inside_and_qualified_outside(build_package):
    source = HEADER + "class A:\n    class B:\n        pass\n\n    inner: B\n\nclass C:\n    outer: A.B\n"
    package = build_package({"a": source})

    a, c = package.modules[0].families

    assert a.nested[0].owner is a
    assert a.declarations[0].fields[0].type == StructRef(a.nested[0])
    assert c.declarations[0].fields[0].type == StructRef(a.nested[0])


def test_import_across_modules_resolves_to_the_family(build_package):
    package = build_package(
        {"a": HEADER + "class A:\n    pass\n", "b": HEADER + "from protocol.a import A\n\nclass B:\n    a: A\n"}
    )

    a = package.modules[0].families[0]
    b = package.modules[1].families[0]

    assert b.declarations[0].fields[0].type == StructRef(a)


def test_imports_bind_their_as_names(build_package):
    source = HEADER + "import uuid as u\nfrom protocol import uint8 as byte\nfrom protocol.a import A as B\n"
    package = build_package(
        {"a": HEADER + "class A:\n    pass\n", "b": source + "class C:\n    x: u.UUID\n    y: byte\n    z: B\n"}
    )

    x, y, z = package.modules[1].families[0].declarations[0].fields

    assert x.type.builtin.name == "UUID"
    assert y.type == Primitive("uint8")
    assert z.type == StructRef(package.modules[0].families[0])


def test_import_across_modules_reaches_only_declared_families(build_package):
    with pytest.raises(CompilerError, match=r"uuid: is not declared in protocol\.a"):
        build_package({"a": HEADER + "import uuid\n", "b": HEADER + "from protocol.a import uuid\n"})


def test_import_may_precede_the_module_it_names(build_package):
    package = build_package(
        {"a": HEADER + "from protocol.b import B\n\nclass A:\n    b: B\n", "b": HEADER + "class B:\n    pass\n"}
    )

    assert package.modules[0].families[0].declarations[0].fields[0].type == StructRef(package.modules[1].families[0])


def test_protocol_exports_only_what_its_init_binds(build_package):
    with pytest.raises(CompilerError, match="uint8: is not exported by protocol"):
        build_package({"a": 'from protocol import uint8\npackage = "a"\n'}, "versions = (1, 2, 3)\n")


def test_class_scopes_resolve_outward_before_the_module(build_package):
    source = HEADER + "class B:\n    pass\n\nclass A:\n    class B:\n        pass\n\n    class C:\n        b: B\n"
    package = build_package({"a": source})

    a = package.modules[0].families[1]

    assert a.nested[1].declarations[0].fields[0].type == StructRef(a.nested[0])


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("class A:\n    x: 'uint8'\n", "string annotations are not allowed"),
        ("class A:\n    x: Missing\n", "Missing: is not defined"),
        ("class A:\n    x: 3\n", "3: is not a type"),
        ("class A:\n    x: print\n", "is not a type"),
        ("class A:\n    x: uint8\n    x: uint8\n", "x: is declared twice"),
        ("class A:\n    x: uint8 = 3\n", "x: is assigned something other than field"),
        ("class A:\n    x: uint8 = packet(id=1)\n", "x: is assigned something other than field"),
        ("class A:\n    x: uint8 = field(bogus=2)\n", "field: got an unexpected keyword argument 'bogus'"),
        ("class A:\n    x = 3\n", "A: holds only fields"),
        ("class A:\n    3\n", "A: holds only fields"),
        ("class A(metaclass=type):\n    pass\n", "A: keywords are not supported"),
        ("@packet\nclass A:\n    pass\n", "A: is decorated with something other than a bare builtin"),
        ("@builtin(uint8)\nclass A:\n    pass\n", "A: is decorated with something other than a bare builtin"),
        ("@packet(id=1, id=2)\nclass A:\n    pass\n", "id: is repeated"),
        ("class A:\n    @builtin\n    class B:\n        pass\n", "B: a builtin is declared at the top"),
        ("@packet()\nclass A:\n    pass\n", "packet: missing a required keyword-only argument: 'id'"),
        ("@packet(id=1, bogus=2)\nclass A:\n    pass\n", "packet: got an unexpected keyword argument 'bogus'"),
        ("@packet(id='1')\nclass A:\n    pass\n", "packet: is not a literal int"),
        ("@packet(id=True)\nclass A:\n    pass\n", "packet: is not a literal int"),
        ("@packet(id=1)\n@type()\nclass A:\n    pass\n", "A: takes only one of packet, type and builtin"),
        ("@print\nclass A:\n    pass\n", "is decorated with something other than"),
        ("@builtin\nclass A:\n    x: uint8\n", "A: a builtin has no body"),
        ("type Id = A\n\nclass A:\n    pass\n", "Id: is not a primitive"),
        ("class A[T]:\n    pass\n", "A: type parameters are not allowed"),
        ("class A:\n    x: __dict__\n", "__dict__: is not a type"),
        ("class A:\n    x: double.__value__\n", r"double\.__value__: is not defined"),
        ("@packet(id=x)\nclass A:\n    pass\n", "packet: is not a literal int"),
        ("@packet(id={[]})\nclass A:\n    pass\n", "packet: is not a literal int"),
        ("type Id[T] = uint8\n", "Id: type parameters are not allowed"),
        ("import os\n", "os: is not an importable module"),
        ("from os import path\n", "os: is not an importable module"),
        ("from enum import Bogus\n", "Bogus: is not exported by enum"),
        ("from protocol import versions\n", "versions: is not exported by protocol"),
        ("from protocol.missing import A\n", "A: is not declared in protocol.missing"),
        ("x = 3\n", "module: holds only imports"),
        ('x = "a"\n', "module: holds only imports"),
        ("package = 3\n", "module: holds only imports"),
        ('package = "bedrock.protocol"\n', "package: is declared twice"),
        ("from . import a\n", r"\.: is not an importable module"),
        ("from .enum import IntEnum\n", r"\.enum: is not an importable module"),
        ("class A:\n    x: uint8 = field(**{})\n", "field: takes its arguments written out"),
        ("class A:\n    x: uint8 = field(*x)\n", "field: takes its arguments written out"),
        ("class A:\n    x: foo().bar\n", r"foo\(\): is not a name"),
        ("class uint8:\n    pass\n", "uint8: is already declared"),
    ],
)
def test_module_is_rejected(build_package, source, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER + source})


def test_module_without_package_is_rejected(build_package):
    with pytest.raises(CompilerError, match=r"a\.py: package: missing"):
        build_package({"a": "class A:\n    pass\n"})


def test_family_name_repeated_across_modules_is_rejected(build_package):
    with pytest.raises(CompilerError, match="A: is already declared"):
        build_package({"a": HEADER + "class A:\n    pass\n", "b": HEADER + "class A:\n    pass\n"})


def test_error_names_the_file_and_position(build_package):
    with pytest.raises(CompilerError, match=r"protocol/a.py:5:8: Missing: is not defined"):
        build_package({"a": HEADER + "class A:\n    x: Missing\n"})


@pytest.mark.parametrize(
    ("init", "message"),
    [
        ("", "versions: missing"),
        ("versions = (2, 1)\n", "versions: is not a tuple of ascending integers"),
        ("versions = (1, 1)\n", "versions: is not a tuple of ascending integers"),
        ("versions = ()\n", "versions: is not a tuple of ascending integers"),
        ("versions = [1, 2, 3]\n", "versions: is not a tuple of ascending integers"),
        ("versions = x\n", "versions: is not a tuple of ascending integers"),
        ("versions = {[]}\n", "versions: is not a tuple of ascending integers"),
        ("versions = (1, 'a')\n", "versions: is not a tuple of ascending integers"),
        ("versions = (True, 2)\n", "versions: is not a tuple of ascending integers"),
        ("versions = (1, 2, 3)\nversions = (1, 2, 3)\n", "versions: is declared twice"),
        ("versions = (1, 2, 3)\n__version__ = 3\n", "module: holds only imports"),
        ("versions = (1, 2, 3)\nclass A:\n    pass\n", "module: holds only imports"),
        ("from protocol.a import A\nversions = (1, 2, 3)\n", "protocol.a: is not importable from __init__"),
    ],
)
def test_init_is_rejected(build_package, init, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER}, init)


def test_package_without_init_is_rejected(tmp_path):
    with pytest.raises(CompilerError, match=r"__init__\.py: missing"):
        build(tmp_path)


def test_a_module_lists_its_families_in_source_order(build_package):
    source = (
        HEADER + "class A:\n    x: uint8\n\n@type(cereal=False)\nclass B:\n    x: uint8\n\nclass B:\n    x: uint8\n"
    )
    package = build_package({"a": source})

    assert [(family.name, family.cereal) for family in package.modules[0].families] == [
        ("A", True),
        ("B", False),
        ("B", True),
    ]
