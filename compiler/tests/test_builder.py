import pytest

from bedrock_protocol_compiler.descriptor import (
    Alias,
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
    package = build_package({"a": HEADER + "class A:\n    pass\n", "b": HEADER})

    assert package.versions == (1, 2, 3)
    assert [(module.stem, module.package) for module in package.modules] == [
        ("a", "bedrock.protocol"),
        ("b", "bedrock.protocol"),
    ]


def test_struct_fields_keep_declaration_order(build_package):
    package = build_package({"a": HEADER + "class A:\n    x: uint8\n    y: double\n    z: str\n    w: bytes\n"})

    struct = package.modules[0].families[0]

    assert [(field.name, field.type) for field in struct.declarations[0].fields] == [
        ("x", Primitive("uint8")),
        ("y", Primitive("double")),
        ("z", Primitive("str")),
        ("w", Primitive("bytes")),
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


def test_import_may_precede_the_module_it_names(build_package):
    package = build_package(
        {"a": HEADER + "from protocol.b import B\n\nclass A:\n    b: B\n", "b": HEADER + "class B:\n    pass\n"}
    )

    assert isinstance(package.modules[0].families[0].declarations[0].fields[0].type, StructRef)


def test_alias_family_is_an_alias(build_package):
    package = build_package({"a": HEADER + "type Id = uint8\n"})

    assert isinstance(package.modules[0].families[0], Alias)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("class A:\n    x: 'uint8'\n", "string annotations are not allowed"),
        ("class A:\n    x: Missing\n", "Missing: is not defined"),
        ("class A:\n    x: uint8 | None\n", "is not supported yet"),
        ("class A:\n    x: print\n", "is not a type"),
        ("class A:\n    x: uint8\n    x: uint8\n", "x: is declared twice"),
        ("class A:\n    x: uint8 = 3\n", "x: is assigned something other than field"),
        ("class A:\n    x: uint8 = field(since=2)\n", "field: since is not supported yet"),
        ("class A:\n    x: uint8 = field(bogus=2)\n", "field: got an unexpected keyword argument 'bogus'"),
        ("class A:\n    x = 3\n", "A: holds only fields"),
        ("class A(Enum):\n    pass\n", "bases are not supported yet"),
        ("@packet\nclass A:\n    pass\n", "packet: "),
        ("@packet()\nclass A:\n    pass\n", "packet: missing a required keyword-only argument: 'id'"),
        ("@packet(id=1, bogus=2)\nclass A:\n    pass\n", "packet: got an unexpected keyword argument 'bogus'"),
        ("@packet(id='1')\nclass A:\n    pass\n", "packet: id is not an integer literal"),
        ("@packet(id=1, since=2)\nclass A:\n    pass\n", "packet: since is not supported yet"),
        ("@packet(id=1)\n@type()\nclass A:\n    pass\n", "A: takes only one of packet, type and builtin"),
        ("@print\nclass A:\n    pass\n", "is decorated with something other than"),
        ("@builtin\nclass A:\n    x: uint8\n", "A: a builtin has no body"),
        ("type Id = A\n\nclass A:\n    pass\n", "Id: is not a primitive"),
        ("type Id[T] = uint8\n", "Id: type parameters are not allowed"),
        ("import os\n", "os: is not an importable module"),
        ("from os import path\n", "os: is not an importable module"),
        ("from protocol import versions\n", "versions: is not exported by protocol"),
        ("from protocol.missing import A\n", "A: is not declared in protocol.missing"),
        ("x = 3\n", "module: holds only imports"),
        ("class A:\n    pass\n\nclass A:\n    pass\n", "A: is already declared"),
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
    with pytest.raises(CompilerError, match=r"protocol/a.py:5:7: Missing: is not defined"):
        build_package({"a": HEADER + "class A:\n    x: Missing\n"})


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("versions = (1, 2, 3)", "", "versions: missing"),
        ("(1, 2, 3)", "(2, 1)", "versions: is not a tuple of ascending integers"),
        ("(1, 2, 3)", "(1, 1)", "versions: is not a tuple of ascending integers"),
        ("(1, 2, 3)", "()", "versions: is not a tuple of ascending integers"),
        ("(1, 2, 3)", "(1, 'a')", "versions: is not a tuple of ascending integers"),
        ("versions = (1, 2, 3)", "class A:\n    pass", "module: holds only imports"),
    ],
)
def test_init_is_rejected(build_package, init_source, old, new, message):
    with pytest.raises(CompilerError, match=message):
        build_package({"a": HEADER}, init_source.replace(old, new))
