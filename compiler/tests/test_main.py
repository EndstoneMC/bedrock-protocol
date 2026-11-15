import os
import re

import pytest

from bedrock_protocol_compiler.__main__ import main

A = """
from enum import IntEnum
from protocol import field, packet, type, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    X = 1

@packet(id=1)
class P:
    e: E = field(type=str)
"""

B = """
from protocol import type, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class B:
    x: uint8
"""


C = """
from protocol import packet, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@packet(id=2)
class Q:
    x: uint8
"""


BITSET = """
from enum import IntEnum
from protocol import bitset, type, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = 1
    B = 2
    COUNT = B

class P:
    x: bitset[E.COUNT]
"""


SENTINEL = """
from enum import IntEnum
from protocol import bitset, field, packet, sentinel, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = 1
    B = 2
    COUNT = sentinel()

class F(IntEnum, uint8):
    A = 1
    COUNT = sentinel()
    LATEST = COUNT - 1

@packet(id=1)
class P:
    e: E = field(type=str)
    width: bitset[E.COUNT]
    x: uint8 = field(when=lambda p: p.e == E.COUNT)
    f: F
"""

DEPRECATED = """
from enum import IntEnum
from protocol import auto, field, packet, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class D(IntEnum, uint8):
    A = 1
    OLD = value(2, "Old_Deprecated", deprecated=True)
    NEXT = auto(deprecated=True)
    LATEST = OLD

@packet(id=1)
class P:
    d: D = field(type=str)
    x: uint8 = field(when=lambda p: p.d == D.OLD)
"""

CYLINDER = """
from protocol import field
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class Vec2:
    x: float
    y: float

class CylinderDataPayload:
    radii: Vec2 = field(duplicate=2)
    height: float
"""

NESTED = """
from protocol import type, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class Inner:
    x: uint8

@type(since=2)
class Outer:
    inner: Inner
"""

RETURNING = """
from protocol import type, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@type(until=3)
class A:
    x: uint8

@type(since=3, until=4)
class A:
    y: uint8

@type(since=4)
class A:
    x: uint8
"""

LISTS = """
from protocol import uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class Item:
    x: uint8

class Bag:
    items: list[Item]
    ids: list[uint8]
"""

BUILTINS = """
from enum import IntEnum
from protocol import bitset, builtin, type, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@builtin
class DynamicValue:
    pass

class E(IntEnum, uint8):
    A = 1
    B = 2
    COUNT = B

@type(since=2)
class P:
    v: DynamicValue
    flags: bitset[E.COUNT]
"""

MAPS = """
from protocol import uint8, uint16
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class Item:
    x: uint8

class Registry:
    items: dict[uint16, Item]
"""

ENCODING = """
from protocol import packet, type, int32, varint32
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@type(until=3)
class S:
    x: varint32

@type(since=3)
class S:
    x: int32

@packet(id=1)
class P:
    s: S
"""

ORDER = """
from protocol import packet, uint8, uint16
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@packet(id=2, until=3)
class Q:
    a: uint8
    b: uint16

@packet(id=2, since=3)
class Q:
    b: uint16
    a: uint8
"""

ENUM_SPLIT = """
from enum import IntEnum
from protocol import uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = 1
    B = value(2, since=3)

class H:
    e: E
"""

MERGED_NEST = """
from protocol import packet, uint8, int32, varint32
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@packet(id=2, until=3)
class T:
    class Child:
        x: uint8

    c: Child
    v: varint32

@packet(id=2, since=3)
class T:
    class Child:
        x: uint8

    c: Child
    v: int32
"""


VERSIONED = """
from protocol import type, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@type(until=3)
class R:
    x: uint8

@type(since=3)
class R:
    x: uint8
    y: uint8
"""

PAIR_EQUAL = """
from protocol import field, packet, type, int32, varint32
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@type(until=3)
class B:
    x: varint32

@type(since=3)
class B:
    x: int32

@type(cereal=False, until=5)
class B:
    x: varint32

@packet(id=1)
class P:
    b: B = field(until=5, cereal=False)
    b: B = field(since=5)

@packet(id=2)
class Q:
    b: B
"""

PAIR_SHARED_LATER = """
from protocol import field, packet, type, int32, uint8, varint32
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@type(until=3)
class G:
    x: varint32
    y: uint8

@type(since=3)
class G:
    x: int32

@type(cereal=False, until=5)
class G:
    x: varint32

@packet(id=1, until=5)
class R:
    g: G = field(cereal=False)
"""

PAIR_DIFFERENT = """
from protocol import field, packet, type, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@type(until=3)
class H:
    x: uint8
    y: uint8

@type(since=3)
class H:
    x: uint8

@type(cereal=False, until=5)
class H:
    x: uint8
    z: uint8

@type(until=3)
class K:
    x: uint8
    y: uint8

@type(since=3)
class K:
    x: uint8

@type(cereal=False, until=5)
class K:
    x: uint8
    z: uint8

@packet(id=1, until=5)
class R:
    h: H = field(cereal=False)
    k: K = field(cereal=False)
"""

PAIR_NEW_ENCODING_AFTER_MIXED = """
from protocol import field, packet, type, int32, varint32
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@type(until=3)
class B:
    x: varint32

@type(since=3, until=5)
class B:
    x: int32

@type(since=5)
class B:
    x: int32 = field(endian="big")

@type(cereal=False, until=5)
class B:
    x: varint32

@packet(id=1)
class P:
    b: B = field(until=5, cereal=False)
    b: B = field(since=5)
"""

ENUM_NAME_LATER = """
from enum import IntEnum
from protocol import field, type, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = 1
    B = value(2, since=3)

@type(since=3)
class T:
    e: dict[E, uint8] = field(type=str)
"""

SHARED_CHILD = """
from enum import IntEnum
from protocol import packet, type, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@type(until=3)
class N:
    class F(IntEnum, uint8):
        A = 1

    f: F

@type(since=3)
class N:
    class F(IntEnum, uint8):
        A = 1

    f: F
    y: uint8

@packet(id=1)
class P:
    n: N
"""

CYLINDER_INIT = """
from bedrock_protocol_compiler.dsl import field

versions = (1001,)

releases = {1001: "1.26.30"}
"""


@pytest.fixture
def generate(build_package, tmp_path):
    def run(modules: dict[str, str], **options):
        build_package(modules, **options)
        main([str(tmp_path / "protocol"), "--out", str(tmp_path / "out")])
        return tmp_path / "out/bedrock/protocol"

    return run


def test_a_header_and_a_source_per_module_packets_hpp_and_version_hpp(generate):
    out = generate({"a": A, "b": B})

    assert sorted(path.name for path in out.iterdir()) == ["a.cpp", "a.h", "b.cpp", "b.h", "packets.hpp", "version.hpp"]


def test_a_second_run_leaves_every_file_untouched(generate, tmp_path):
    out = generate({"a": A})
    for path in out.iterdir():
        os.utime(path, ns=(1_000_000_000, 1_000_000_000))

    main([str(tmp_path / "protocol"), "--out", str(tmp_path / "out")])

    assert {path.stat().st_mtime_ns for path in out.iterdir()} == {1_000_000_000}


def test_a_file_the_schema_no_longer_names_is_deleted(generate, tmp_path):
    out = generate({"a": A, "b": B})
    (tmp_path / "protocol/b.py").unlink()

    main([str(tmp_path / "protocol"), "--out", str(tmp_path / "out")])

    assert sorted(path.name for path in out.iterdir()) == ["a.cpp", "a.h", "packets.hpp", "version.hpp"]


def test_a_schema_error_exits_with_its_message(build_package, tmp_path):
    build_package({"a": B})
    (tmp_path / "protocol/a.py").write_text(
        'package = "bedrock.protocol"\njava_package = "dev.endstone.protocol"\nclass A:\n    x: Missing\n'
    )

    with pytest.raises(SystemExit, match=r"bpc: .*Missing"):
        main([str(tmp_path / "protocol"), "--out", str(tmp_path / "out")])


def test_a_bitset_width_may_name_a_derived_member(generate):
    out = generate({"a": BITSET})

    assert (out / "a.h").exists()


def test_a_sentinel_is_no_enumerator(generate):
    out = generate({"a": SENTINEL})

    assert "enum class E : std::uint8_t {\n    A = 1,\n    B = 2,\n};" in (out / "a.h").read_text()


def test_a_sentinel_has_no_reflected_value_or_name(generate):
    header = (generate({"a": SENTINEL}) / "a.h").read_text()
    values = "values_v<::bedrock::protocol::E>{{\n    ::bedrock::protocol::E::A,\n    ::bedrock::protocol::E::B,\n}};"

    assert values in header
    assert 'names_v<::bedrock::protocol::E>{{\n    "a",\n    "b",\n}};' in header
    assert 'schema_names_v<::bedrock::protocol::E>{{\n    "A",\n    "B",\n}};' in header


def test_a_member_named_after_a_sentinel_takes_its_number(generate):
    out = generate({"a": SENTINEL})

    assert "enum class F : std::uint8_t {\n    A = 1,\n    Latest = 1,\n};" in (out / "a.h").read_text()


def test_a_bitset_is_as_wide_as_the_sentinel_it_names(generate):
    out = generate({"a": SENTINEL})

    assert "std::bitset<3> width{};" in (out / "a.h").read_text()


def test_a_predicate_reads_a_sentinel_as_its_number(generate):
    out = generate({"a": SENTINEL})

    assert "(value.e) == (static_cast<::bedrock::protocol::E>(3))" in (out / "a.cpp").read_text()


def test_a_deprecated_member_is_a_deprecated_enumerator(generate):
    out = generate({"a": DEPRECATED})

    assert "    Old [[deprecated]] = 2,\n    Next [[deprecated]] = 3,\n" in (out / "a.h").read_text()


def test_an_alias_of_a_deprecated_member_spells_its_number(generate):
    out = generate({"a": DEPRECATED})

    assert "    Latest = 2,\n};" in (out / "a.h").read_text()


def test_a_deprecated_member_reflects_its_number_and_encoded_name(generate):
    header = (generate({"a": DEPRECATED}) / "a.h").read_text()
    values = (
        "values_v<::bedrock::protocol::D>{{\n    ::bedrock::protocol::D::Latest,\n    ::bedrock::protocol::D::A,\n"
        "    static_cast<::bedrock::protocol::D>(2),\n    static_cast<::bedrock::protocol::D>(3),\n}};"
    )

    names = 'names_v<::bedrock::protocol::D>{{\n    "latest",\n    "a",\n    "old_deprecated",\n    "next",\n}};'

    assert values in header
    assert names in header


def test_an_enum_with_a_deprecated_member_flags_each_reflected_member(generate):
    header = (generate({"a": DEPRECATED}) / "a.h").read_text()

    assert "deprecated_v<::bedrock::protocol::D>{{\n    false,\n    false,\n    true,\n    true,\n}};" in header


def test_an_enum_without_a_deprecated_member_has_no_deprecated_flags(generate):
    out = generate({"a": SENTINEL})

    assert "deprecated_v" not in (out / "a.h").read_text()


def test_a_predicate_reads_a_deprecated_member_as_its_number(generate):
    out = generate({"a": DEPRECATED})

    assert "(value.d) == (static_cast<::bedrock::protocol::D>(2))" in (out / "a.cpp").read_text()


def test_a_schema_error_leaves_the_output_tree_untouched(generate, tmp_path):
    out = generate({"a": A, "b": B})
    before = {path.name: path.read_bytes() for path in out.iterdir()}
    for path in out.iterdir():
        os.utime(path, ns=(1_000_000_000, 1_000_000_000))
    (tmp_path / "protocol/b.py").write_text(
        'package = "bedrock.protocol"\njava_package = "dev.endstone.protocol"\nclass B:\n    x: Missing\n'
    )

    with pytest.raises(SystemExit, match=r"bpc: .*Missing"):
        main([str(tmp_path / "protocol"), "--out", str(tmp_path / "out")])

    assert {path.name: path.read_bytes() for path in out.iterdir()} == before
    assert {path.stat().st_mtime_ns for path in out.iterdir()} == {1_000_000_000}


def test_packets_hpp_names_every_packet_of_every_module(generate):
    out = generate({"a": A, "c": C})

    registry = (out / "packets.hpp").read_text()
    assert "struct packet_of<V, 1>" in registry
    assert "struct packet_of<V, 2>" in registry


def test_a_module_header_specialises_no_packet_of(generate):
    out = generate({"a": A})

    assert "packet_of" not in (out / "a.h").read_text()


def test_packets_hpp_includes_every_module_header(generate):
    out = generate({"a": A, "b": B})

    assert "#include <bedrock/protocol/b.h>" in (out / "packets.hpp").read_text()


def test_version_hpp_gives_a_release_the_newest_snapshot_at_or_below_it(generate):
    init = """
from bedrock_protocol_compiler.dsl import field, packet, type, uint8

versions = (1, 2, 4)

releases = {1: "1.1.0", 2: "1.2.0", 3: "1.3.0", 4: "1.4.x"}
"""

    out = generate({"a": A}, init=init)

    version = (out / "version.hpp").read_text()
    assert 'ProtocolVersion{3, 2, "1.3.0", "1.3.0", "1.3.0"},' in version
    assert 'ProtocolVersion{4, 4, "1.4.x", "1.4.0", "1.4.9"},' in version


def test_a_duplicated_field_writes_once_per_copy(generate):
    out = generate({"a": CYLINDER}, init=CYLINDER_INIT)

    write = (
        "    for (std::size_t copy = 0; copy < 2; ++copy) {\n"
        "        {\n"
        "            auto r = Serializer<::bedrock::protocol::Vec2, 1001>::serialize(stream, value.radii);\n"
        '            if (!r) return stream.fail(r.error(), "radii");\n'
        "        }\n"
        "    }\n"
        "    stream.write<float>(value.height);\n"
    )
    assert write in (out / "a.cpp").read_text()


def test_a_duplicated_field_reads_every_copy_into_it(generate):
    out = generate({"a": CYLINDER}, init=CYLINDER_INIT)

    read = (
        "    for (std::size_t copy = 0; copy < 2; ++copy) {\n"
        "        {\n"
        "            auto v = Serializer<::bedrock::protocol::Vec2, 1001>::deserialize(stream);\n"
        '            if (!v) return stream.fail(v.error(), "radii");\n'
        "            out.radii = std::move(*v);\n"
        "        }\n"
        "    }\n"
    )
    assert read in (out / "a.cpp").read_text()


def test_an_implementation_is_named_for_its_shapes_first_protocol(generate):
    out = generate({"a": NESTED})

    assert "struct Serializer<::bedrock::protocol::Outer, 2> {\n" in (out / "a.h").read_text()
    assert "auto Serializer<::bedrock::protocol::Outer, 2>::serialize(" in (out / "a.cpp").read_text()


def test_an_implementation_carries_its_first_protocol_as_since(generate):
    out = generate({"a": NESTED})

    assert "    static constexpr int since = 2;\n" in (out / "a.h").read_text()


def test_a_run_gets_a_partial_bounded_by_it(generate):
    out = generate({"a": NESTED})

    partial = (
        "template <int V> requires (V >= 2)\n"
        "struct Serializer<::bedrock::protocol::Outer, V> : Serializer<::bedrock::protocol::Outer, 2> {};\n"
    )
    assert partial in (out / "a.h").read_text()


def test_a_shape_live_at_every_version_gets_an_unconstrained_partial(generate):
    out = generate({"a": NESTED})

    partial = (
        "template <int V>\n"
        "struct Serializer<::bedrock::protocol::Inner, V> : Serializer<::bedrock::protocol::Inner, 1> {};\n"
    )
    assert partial in (out / "a.h").read_text()


def test_a_shape_live_in_two_runs_gets_a_partial_per_run(generate):
    out = generate({"a": RETURNING})

    header = (out / "a.h").read_text()
    assert (
        "template <int V> requires (V < 3)\n"
        "struct Serializer<::bedrock::protocol::A, V> : Serializer<::bedrock::protocol::A, 1> {};\n"
    ) in header
    assert (
        "template <int V> requires (V >= 4)\n"
        "struct Serializer<::bedrock::protocol::A, V> : Serializer<::bedrock::protocol::A, 1> {};\n"
    ) in header


def test_a_child_call_names_the_childs_own_protocol(generate):
    out = generate({"a": NESTED})

    assert (
        "auto r = Serializer<::bedrock::protocol::Inner, 1>::serialize(stream, value.inner);"
        in (out / "a.cpp").read_text()
    )


def test_a_failed_nested_write_names_its_field(generate):
    out = generate({"a": NESTED})

    assert 'if (!r) return stream.fail(r.error(), "inner");' in (out / "a.cpp").read_text()


def test_a_failing_list_element_carries_its_index(generate):
    out = generate({"a": LISTS})

    write = (
        "    for (std::size_t i0 = 0; const auto &e0 : value.items) {\n"
        "        {\n"
        "            auto r = Serializer<::bedrock::protocol::Item, 1>::serialize(stream, e0);\n"
        '            if (!r) return stream.fail(r.error(), "items", i0);\n'
        "        }\n"
        "        ++i0;\n"
        "    }\n"
    )
    assert write in (out / "a.cpp").read_text()


def test_a_list_of_primitives_keeps_its_unindexed_loop(generate):
    out = generate({"a": LISTS})

    write = (
        "    stream.writeVarInt<std::uint32_t>(value.ids.size());\n"
        "    for (const auto &e0 : value.ids) {\n"
        "        stream.write<std::uint8_t>(e0);\n"
        "    }\n"
        "    return {};\n"
    )
    assert write in (out / "a.cpp").read_text()


def test_a_name_coded_write_rejects_a_value_with_no_name(generate):
    out = generate({"a": A})

    write = (
        "auto Serializer<::bedrock::protocol::E, 1>::serialize(BinaryWriter &stream, ::bedrock::protocol::E value)"
        " -> std::expected<void, Errc>\n"
        "{\n"
        "    if (!enum_contains(value)) return std::unexpected(Errc::unknown_value);\n"
        "    stream.write(enum_name(value));\n"
        "    return {};\n"
        "}\n"
    )
    assert write in (out / "a.cpp").read_text()


def test_an_explicit_specialization_comes_before_its_partials(generate):
    out = generate({"a": NESTED})

    order = (
        "    static auto deserialize(BinaryReader &stream) -> std::expected<::bedrock::protocol::Outer, Errc>;\n"
        "};\n"
        "\n"
        "template <int V> requires (V >= 2)\n"
        "struct Serializer<::bedrock::protocol::Outer, V>"
    )
    assert order in (out / "a.h").read_text()


def test_a_builtin_is_called_with_the_callers_protocol(generate):
    out = generate({"a": BUILTINS})

    assert (
        "auto r = Serializer<::bedrock::protocol::DynamicValue, 2>::serialize(stream, value.v);"
        in (out / "a.cpp").read_text()
    )


def test_a_bitset_is_called_with_the_callers_protocol(generate):
    out = generate({"a": BUILTINS})

    assert "auto r = Serializer<std::bitset<2>, 2>::serialize(stream, value.flags);" in (out / "a.cpp").read_text()


def test_a_map_whose_value_can_fail_carries_an_index(generate):
    out = generate({"a": MAPS})

    write = (
        "    for (std::size_t i0 = 0; const auto &[k0, v0] : value.items) {\n"
        "        stream.write<std::uint16_t>(k0);\n"
        "        {\n"
        "            auto r = Serializer<::bedrock::protocol::Item, 1>::serialize(stream, v0);\n"
        '            if (!r) return stream.fail(r.error(), "items", i0);\n'
        "        }\n"
        "        ++i0;\n"
        "    }\n"
    )
    assert write in (out / "a.cpp").read_text()


def body_of(source, signature):
    return source.partition(signature)[2].partition("\n}\n")[0]


def test_an_encoding_only_difference_shares_one_struct(generate):
    header = (generate({"a": ENCODING}) / "a.h").read_text()

    assert header.count("\nstruct S {\n") == 1


@pytest.mark.parametrize("since", [1, 3], ids=["first-encoding", "second-encoding"])
def test_an_encoding_gets_one_implementation_named_for_its_first_protocol(generate, since):
    header = (generate({"a": ENCODING}) / "a.h").read_text()

    assert f"template <>\nstruct Serializer<::bedrock::protocol::S, {since}> {{\n" in header


@pytest.mark.parametrize("since", [1, 3], ids=["first-encoding", "second-encoding"])
def test_an_implementation_carries_its_first_protocol_as_since_on_its_explicit_specialization(generate, since):
    header = (generate({"a": ENCODING}) / "a.h").read_text()

    assert (
        f"struct Serializer<::bedrock::protocol::S, {since}> {{\n"
        f"    static constexpr int since = {since};\n"
        "    static auto serialize("
    ) in header


@pytest.mark.parametrize(
    ("bound", "since"),
    [("V < 3", 1), ("V >= 3", 3)],
    ids=["first-encoding", "second-encoding"],
)
def test_an_encodings_partial_covers_its_run(generate, bound, since):
    header = (generate({"a": ENCODING}) / "a.h").read_text()

    assert (
        f"template <int V> requires ({bound})\n"
        f"struct Serializer<::bedrock::protocol::S, V> : Serializer<::bedrock::protocol::S, {since}> {{}};\n"
    ) in header


@pytest.mark.parametrize("since", [1, 3], ids=["first-encoding", "second-encoding"])
def test_a_parent_calls_the_child_encoding_of_its_own_encoding(generate, since):
    source = (generate({"a": ENCODING}) / "a.cpp").read_text()

    body = body_of(source, f"auto Serializer<::bedrock::protocol::P, {since}>::serialize(")
    assert f"auto r = Serializer<::bedrock::protocol::S, {since}>::serialize(stream, value.s);" in body


def test_a_shared_struct_lists_its_members_in_the_newest_order(generate):
    header = (generate({"a": ORDER}) / "a.h").read_text()

    assert "    std::uint16_t b{};\n    std::uint8_t a{};\n" in header
    assert "    std::uint8_t a{};\n    std::uint16_t b{};\n" not in header


def test_the_older_encoding_of_a_shared_struct_writes_in_its_own_order(generate):
    source = (generate({"a": ORDER}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::Q, 1>::serialize(")
    assert "    stream.write<std::uint8_t>(value.a);\n    stream.write<std::uint16_t>(value.b);\n" in body


def test_a_referenced_enum_shape_change_still_splits_the_struct(generate):
    header = (generate({"a": ENUM_SPLIT}) / "a.h").read_text()

    assert "struct Serializer<::bedrock::protocol::v1::H, 1> {\n" in header
    assert "struct Serializer<::bedrock::protocol::H, 3> {\n" in header


def test_a_hand_written_form_with_equal_members_shares_the_cereal_struct(generate):
    header = (generate({"a": PAIR_EQUAL}) / "a.h").read_text()

    assert header.count("\nstruct B {\n") == 1
    assert "::bedrock::protocol::v1::B" not in header


@pytest.mark.parametrize("since", [1, 3], ids=["first-encoding", "second-encoding"])
def test_a_shared_type_has_an_explicit_specialization_per_encoding(generate, since):
    header = (generate({"a": PAIR_EQUAL}) / "a.h").read_text()

    assert (
        f"template <>\nstruct Serializer<::bedrock::protocol::B, {since}, SerializationMode::Cereal> {{\n"
        f"    static constexpr int since = {since};\n"
    ) in header


@pytest.mark.parametrize(
    ("bound", "since"),
    [("V < 3", 1), ("V >= 3 && V < 5", 3)],
    ids=["first-encoding", "second-encoding"],
)
def test_a_shared_type_has_a_cereal_partial_per_run(generate, bound, since):
    header = (generate({"a": PAIR_EQUAL}) / "a.h").read_text()

    assert (
        f"template <int V> requires ({bound})\n"
        "struct Serializer<::bedrock::protocol::B, V, SerializationMode::Cereal> : "
        f"Serializer<::bedrock::protocol::B, {since}, SerializationMode::Cereal> {{}};\n"
    ) in header


def test_a_tie_between_the_forms_is_keyed_cereal_with_a_manual_partial_inheriting_from_it(generate):
    header = (generate({"a": PAIR_EQUAL}) / "a.h").read_text()

    assert "struct Serializer<::bedrock::protocol::B, 1, SerializationMode::Manual> {" not in header
    assert (
        "template <int V> requires (V < 5)\n"
        "struct Serializer<::bedrock::protocol::B, V, SerializationMode::Manual> : "
        "Serializer<::bedrock::protocol::B, 1, SerializationMode::Cereal> {};\n"
    ) in header


def test_only_the_default_partial_after_the_last_mixed_version_covers_the_default_mode(generate):
    header = (generate({"a": PAIR_EQUAL}) / "a.h").read_text()

    partials = re.findall(r"template <int V>[^\n]*\nstruct Serializer<::bedrock::protocol::B, V> : [^\n]*\n", header)
    assert partials == [
        "template <int V> requires (V >= 5)\n"
        "struct Serializer<::bedrock::protocol::B, V> : "
        "Serializer<::bedrock::protocol::B, 3, SerializationMode::Cereal> {};\n"
    ]


def test_no_cereal_or_manual_partial_reaches_a_version_after_the_last_mixed_one(generate):
    header = (generate({"a": PAIR_EQUAL}) / "a.h").read_text()

    heads = re.findall(r"struct Serializer<::bedrock::protocol::B, V, SerializationMode::\w+> :", header)
    bounds = re.findall(
        r"template <int V> requires \(([^)]*)\)\n"
        r"struct Serializer<::bedrock::protocol::B, V, SerializationMode::\w+> :",
        header,
    )
    assert len(bounds) == len(heads) > 0
    assert max(int(bound.rsplit("V < ", 1)[1]) for bound in bounds) == 5


@pytest.mark.parametrize(
    ("module", "name"),
    [(PAIR_EQUAL, "B"), (PAIR_SHARED_LATER, "G"), (ENCODING, "S")],
    ids=["tie", "distinct-keys", "default-keys"],
)
def test_every_partial_inherits_directly_from_an_explicit_specialization(generate, module, name):
    header = (generate({"a": module}) / "a.h").read_text()

    mode = r"(?:, SerializationMode::(\w+))?"
    qualified = rf"::bedrock::protocol::{name}"
    bases = set(
        re.findall(
            rf"struct Serializer<{qualified}, V(?:, SerializationMode::\w+)?> : "
            rf"Serializer<{qualified}, (\d+){mode}> \{{\}};",
            header,
        )
    )
    explicit = set(re.findall(rf"template <>\nstruct Serializer<{qualified}, (\d+){mode}> \{{\n", header))
    assert bases
    assert bases <= explicit


def test_a_cereal_false_field_calls_the_child_with_the_manual_mode(generate):
    source = (generate({"a": PAIR_EQUAL}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 1>::serialize(")
    assert (
        "auto r = Serializer<::bedrock::protocol::B, 1, SerializationMode::Manual>::serialize(stream, value.b);" in body
    )


@pytest.mark.parametrize("since", [1, 3], ids=["first-encoding", "second-encoding"])
def test_a_plain_field_of_a_cereal_parent_calls_the_child_with_the_cereal_mode(generate, since):
    source = (generate({"a": PAIR_EQUAL}) / "a.cpp").read_text()

    body = body_of(source, f"auto Serializer<::bedrock::protocol::Q, {since}>::serialize(")
    assert (
        f"auto r = Serializer<::bedrock::protocol::B, {since}, SerializationMode::Cereal>::serialize(stream, value.b);"
        in body
    )


def test_a_field_to_a_type_with_one_mode_names_no_mode(generate):
    source = (generate({"a": ENCODING}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 1>::serialize(")
    assert "auto r = Serializer<::bedrock::protocol::S, 1>::serialize(stream, value.s);" in body
    assert "SerializationMode::" not in body


def test_a_child_born_mixed_is_called_by_its_key_mode_from_a_later_unmixed_version(generate):
    source = (generate({"a": PAIR_EQUAL}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 5>::serialize(")
    assert (
        "auto r = Serializer<::bedrock::protocol::B, 3, SerializationMode::Cereal>::serialize(stream, value.b);" in body
    )


@pytest.mark.parametrize("member", ["serialize", "deserialize"])
def test_the_definition_of_a_keyed_implementation_carries_its_mode(generate, member):
    source = (generate({"a": PAIR_EQUAL}) / "a.cpp").read_text()

    assert f"auto Serializer<::bedrock::protocol::B, 3, SerializationMode::Cereal>::{member}(" in source


def test_an_equal_pair_is_selected_by_its_primary_definition_and_has_no_cerealized_selector(generate):
    header = (generate({"a": PAIR_EQUAL}) / "a.h").read_text()

    assert "template <int V>\nstruct B_ { using type = ::bedrock::protocol::B; };\n" in header
    assert "CerealizedB" not in header


def test_a_shared_type_is_listed_once_in_every_types_list(generate):
    header = (generate({"a": PAIR_EQUAL}) / "a.h").read_text()

    lists = re.findall(r"using types = type_list<(.*?)>;", header, re.S)
    assert {len(re.findall(r"::bedrock::protocol::(?:v\d+::)?B\b", text)) for text in lists} == {1}


def test_a_hand_written_form_equal_to_a_later_cereal_model_shares_its_struct(generate):
    header = (generate({"a": PAIR_SHARED_LATER}) / "a.h").read_text()

    assert header.count("\nstruct G {\n") == 1


@pytest.mark.parametrize(
    ("since", "mode"),
    [(1, "Manual"), (3, "Cereal")],
    ids=["hand-written-encoding", "cereal-encoding"],
)
def test_a_shared_type_keys_each_encoding_by_the_mode_that_introduced_it(generate, since, mode):
    header = (generate({"a": PAIR_SHARED_LATER}) / "a.h").read_text()

    assert (
        f"template <>\nstruct Serializer<::bedrock::protocol::G, {since}, SerializationMode::{mode}> {{\n"
        f"    static constexpr int since = {since};\n"
    ) in header


def test_a_manual_partial_covers_the_hand_written_run_of_a_shared_type(generate):
    header = (generate({"a": PAIR_SHARED_LATER}) / "a.h").read_text()

    assert (
        "template <int V> requires (V < 5)\n"
        "struct Serializer<::bedrock::protocol::G, V, SerializationMode::Manual> : "
        "Serializer<::bedrock::protocol::G, 1, SerializationMode::Manual> {};\n"
    ) in header


def test_a_cereal_partial_covers_the_mixed_run_and_a_default_partial_the_unmixed_run(generate):
    header = (generate({"a": PAIR_SHARED_LATER}) / "a.h").read_text()

    assert (
        "template <int V> requires (V >= 3 && V < 5)\n"
        "struct Serializer<::bedrock::protocol::G, V, SerializationMode::Cereal> : "
        "Serializer<::bedrock::protocol::G, 3, SerializationMode::Cereal> {};\n"
    ) in header
    assert (
        "template <int V> requires (V >= 5)\n"
        "struct Serializer<::bedrock::protocol::G, V> : "
        "Serializer<::bedrock::protocol::G, 3, SerializationMode::Cereal> {};\n"
    ) in header


def test_a_cereal_model_that_differs_only_until_some_version_is_declared_prefixed(generate):
    header = (generate({"a": PAIR_SHARED_LATER}) / "a.h").read_text()

    assert "struct CerealizedG {\n" in header
    assert "struct Serializer<::bedrock::protocol::v1::CerealizedG, 1, SerializationMode::Cereal> {\n" in header


def test_a_cerealized_selector_stops_at_the_last_version_where_the_forms_differ(generate):
    header = (generate({"a": PAIR_SHARED_LATER}) / "a.h").read_text()

    assert (
        "template <int V>\n"
        "struct CerealizedG_;\n"
        "\n"
        "template <int V> requires (V < 3)\n"
        "struct CerealizedG_<V> { using type = ::bedrock::protocol::v1::CerealizedG; };\n"
    ) in header
    assert header.count("struct CerealizedG_<V> {") == 1


def test_the_shared_type_of_a_pair_that_differs_only_until_some_version_is_selected_by_the_plain_selector(generate):
    header = (generate({"a": PAIR_SHARED_LATER}) / "a.h").read_text()

    assert "template <int V>\nstruct G_ { using type = ::bedrock::protocol::G; };\n" in header


def test_a_selector_picks_the_hand_written_model_where_the_forms_differ(generate):
    header = (generate({"a": PAIR_DIFFERENT}) / "a.h").read_text()

    assert ("template <int V> requires (V < 5)\nstruct H_<V> { using type = ::bedrock::protocol::v1::H; };\n") in header


def test_a_selector_picks_the_cereal_model_after_the_forms_stop_differing(generate):
    header = (generate({"a": PAIR_DIFFERENT}) / "a.h").read_text()

    assert ("template <int V> requires (V >= 5)\nstruct H_<V> { using type = ::bedrock::protocol::H; };\n") in header


def test_a_cerealized_selector_has_a_partial_per_cereal_model_inside_the_overlap(generate):
    header = (generate({"a": PAIR_DIFFERENT}) / "a.h").read_text()

    assert (
        "template <int V> requires (V < 3)\n"
        "struct CerealizedH_<V> { using type = ::bedrock::protocol::v1::CerealizedH; };\n"
    ) in header
    assert (
        "template <int V> requires (V >= 3 && V < 5)\n"
        "struct CerealizedH_<V> { using type = ::bedrock::protocol::H; };\n"
    ) in header


def test_a_cerealized_selector_stops_at_the_end_of_the_overlap(generate):
    header = (generate({"a": PAIR_DIFFERENT}) / "a.h").read_text()

    assert header.count("struct CerealizedH_<V> {") == 2


def test_a_cereal_model_living_past_the_overlap_is_declared_plain(generate):
    header = (generate({"a": PAIR_DIFFERENT}) / "a.h").read_text()

    assert "\nstruct H {\n    std::uint8_t x{};\n\n    friend" in header
    assert header.count("struct CerealizedH {") == 1


def test_a_cereal_model_living_only_inside_the_overlap_is_declared_prefixed(generate):
    header = (generate({"a": PAIR_DIFFERENT}) / "a.h").read_text()

    assert "struct CerealizedH {\n" in header
    assert "struct Serializer<::bedrock::protocol::v1::CerealizedH, 1, SerializationMode::Cereal> {\n" in header


def test_a_cereal_type_below_the_end_of_the_overlap_is_labelled(generate):
    header = (generate({"a": PAIR_DIFFERENT}) / "a.h").read_text()

    assert (
        "    using labelled = type_list<\n"
        "        ::bedrock::protocol::H,\n"
        "        ::bedrock::protocol::K>;\n"
        "    static constexpr std::array<std::string_view, 2> labels{{\n"
        '        "CerealizedH",\n'
        '        "CerealizedK",\n'
        "    }};\n"
    ) in header


def test_a_types_list_holds_the_hand_written_only_models_of_a_mixed_version(generate):
    header = (generate({"a": PAIR_DIFFERENT}) / "a.h").read_text()

    assert (
        "template <int V> requires (V < 3)\n"
        "struct a_types<V> {\n"
        "    using types = type_list<\n"
        "        ::bedrock::protocol::v1::CerealizedH,\n"
        "        ::bedrock::protocol::v1::H,\n"
        "        ::bedrock::protocol::v1::CerealizedK,\n"
        "        ::bedrock::protocol::v1::K,\n"
        "        ::bedrock::protocol::v1::R>;\n"
    ) in header


def test_a_type_declared_with_its_label_is_not_labelled(generate):
    header = (generate({"a": PAIR_DIFFERENT}) / "a.h").read_text()

    assert re.search(r"requires \(V < 3\)\nstruct a_types<V> \{[^}]*using labelled = type_list<>;", header)


def test_a_type_at_the_end_of_the_overlap_has_no_label(generate):
    header = (generate({"a": PAIR_DIFFERENT}) / "a.h").read_text()

    assert re.search(r"requires \(V >= 5\)\nstruct a_types<V> \{[^}]*using labelled = type_list<>;", header)


def test_a_nested_child_is_owned_by_its_newest_holder(generate):
    header = (generate({"a": SHARED_CHILD}) / "a.h").read_text()

    assert "    using F = ::bedrock::protocol::N_nested::F;\n" in header


def test_a_nested_child_is_defined_before_its_first_holder(generate):
    header = (generate({"a": SHARED_CHILD}) / "a.h").read_text()

    assert (
        "namespace N_nested {\n"
        "\n"
        "enum class F : std::uint8_t {\n"
        "    A = 1,\n"
        "};\n"
        "\n"
        "}  // namespace N_nested\n"
        "\n"
        "namespace v1 {\n"
        "\n"
        "struct N {\n"
    ) in header
    assert header.count("enum class F ") == 1


def test_an_unversioned_family_is_selected_by_its_primary_definition_alone(generate):
    header = (generate({"a": ENCODING}) / "a.h").read_text()

    assert "template <int V>\nstruct P_ { using type = ::bedrock::protocol::P; };\n" in header


def test_reflection_is_emitted_once_for_a_shared_struct(generate):
    header = (generate({"a": ENCODING}) / "a.h").read_text()

    assert header.count("is_reflected_struct_v<::bedrock::protocol::S> = true;") == 1
    assert header.count("field_names_v<::bedrock::protocol::S>{{") == 1


def test_an_empty_labels_array_is_spelled_with_empty_braces(generate):
    header = (generate({"a": PAIR_DIFFERENT}) / "a.h").read_text()

    assert "    static constexpr std::array<std::string_view, 0> labels{};\n};\n" in header


def test_an_owner_is_listed_before_its_nested_children(generate):
    header = (generate({"a": MERGED_NEST}) / "a.h").read_text()

    assert (
        "    using types = type_list<\n"
        "        ::bedrock::protocol::T,\n"
        "        ::bedrock::protocol::T_nested::Child>;\n"
    ) in header


def test_a_cerealized_model_reflects_its_declared_name(generate):
    header = (generate({"a": PAIR_DIFFERENT}) / "a.h").read_text()

    assert 'struct_name_v<::bedrock::protocol::v1::CerealizedH>{"CerealizedH"};' in header


def test_packet_of_names_a_merged_packet_bare(generate):
    registry = (generate({"a": ENCODING}) / "packets.hpp").read_text()

    assert "struct packet_of<V, 1> { using type = ::bedrock::protocol::P; };" in registry


def test_a_nested_struct_under_a_merged_owner_is_declared_in_its_owners_nested_namespace(generate):
    header = (generate({"a": MERGED_NEST}) / "a.h").read_text()

    assert "namespace T_nested {\n\nstruct Child {\n" in header
    assert "    using Child = ::bedrock::protocol::T_nested::Child;\n" in header


def test_the_output_holds_no_pre_cereal_name(generate):
    out = generate({"a": PAIR_DIFFERENT})

    assert "pre_cereal" not in "".join(path.read_text() for path in sorted(out.iterdir()))


def test_the_model_live_at_the_latest_version_is_declared_bare_and_an_older_one_under_its_first_version(generate):
    header = (generate({"a": VERSIONED}) / "a.h").read_text()

    assert "namespace v1 {\n\nstruct R {\n    std::uint8_t x{};\n" in header
    assert "struct Serializer<::bedrock::protocol::v1::R, 1> {\n" in header
    assert "struct Serializer<::bedrock::protocol::R, 3> {\n" in header


def test_no_alias_is_emitted_for_a_family_with_several_models(generate):
    header = (generate({"a": VERSIONED}) / "a.h").read_text()

    assert "template <int V> using R_ = typename detail::R_<V>::type;\n" in header
    assert "using R = R_<5>;" not in header


def test_a_map_read_declares_its_key_and_mapped_types_from_the_container(generate):
    source = (generate({"a": MAPS}) / "a.cpp").read_text()

    assert "            std::map<std::uint16_t, ::bedrock::protocol::Item>::key_type key0{};\n" in source
    assert "            std::map<std::uint16_t, ::bedrock::protocol::Item>::mapped_type element0{};\n" in source


def test_an_encoding_first_used_after_the_mixed_run_has_an_explicit_specialization_with_no_mode(generate):
    header = (generate({"a": PAIR_NEW_ENCODING_AFTER_MIXED}) / "a.h").read_text()

    assert (
        "template <>\nstruct Serializer<::bedrock::protocol::B, 5> {\n    static constexpr int since = 5;\n"
    ) in header


def test_no_explicit_specialization_at_or_past_the_end_of_the_mixed_run_carries_a_mode(generate):
    header = (generate({"a": PAIR_NEW_ENCODING_AFTER_MIXED}) / "a.h").read_text()

    keyed = re.findall(
        r"template <>\nstruct Serializer<::bedrock::protocol::B, (\d+), SerializationMode::\w+> \{\n", header
    )
    assert keyed
    assert max(int(since) for since in keyed) < 5


def test_a_name_coded_enum_inside_a_map_read_is_spelled_by_the_shape_live_where_its_struct_is(generate):
    source = (generate({"a": ENUM_NAME_LATER}) / "a.cpp").read_text()

    assert "            std::map<::bedrock::protocol::E, std::uint8_t>::key_type key0{};\n" in source
