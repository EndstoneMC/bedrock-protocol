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

ENUM_RENUMBERED = """
from enum import IntEnum
from protocol import uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = 1
    B = value(2, until=3)
    B = value(3, since=3)

class H:
    e: E
"""

ENUM_SHARED_VALUE = """
from enum import IntEnum
from protocol import int32, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, int32):
    Old = value(1, until=3)
    Mid = 2
    New = value(1, since=3)
    Alias = 2

class H:
    e: E
"""

ENUM_LATE = """
from enum import IntEnum
from protocol import packet, type, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@type(since=3)
class Z(IntEnum, uint8):
    A = 1
    B = value(2, since=4)

@packet(id=1, since=3)
class P:
    z: Z
"""

ENUM_ENDED = """
from enum import IntEnum
from protocol import packet, type, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@type(until=4)
class F(IntEnum, uint8):
    A = 1
    B = value(2, since=3)

@packet(id=1, until=4)
class P:
    f: F
"""

SHARED_CHILD_GAIN = """
from enum import IntEnum
from protocol import packet, type, uint8, value
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
        B = value(2, since=4)

    f: F
    y: uint8

@packet(id=1)
class P:
    n: N
"""

ENUM_RENAMED_NAME = """
from enum import IntEnum
from protocol import field, packet, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = value(1, 'old', until=3)
    A = value(1, 'new', since=3)

@packet(id=1)
class P:
    e: E = field(type=str)
"""

ENUM_NAME_GAINED = """
from enum import IntEnum
from protocol import field, packet, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = 1
    B = value(2, since=3)

@packet(id=1)
class P:
    e: E = field(type=str)
"""

ENUM_DERIVED_MEMBER = """
from enum import IntEnum
from typing import Literal
from protocol import field, packet, sentinel, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = 1
    B = value(2, since=3)
    COUNT = sentinel()
    LATEST = COUNT - 1

@packet(id=1)
class P:
    e: E
    tag: Literal[E.LATEST]
"""

ENUM_DEPRECATED_GAIN = """
from enum import IntEnum
from protocol import uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class D(IntEnum, uint8):
    A = 1
    OLD = value(2, deprecated=True)
    B = value(3, since=3)

class H:
    d: D
"""

ENUM_ASYMMETRIC = """
from enum import IntEnum
from protocol import uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = 1
    B = value(2, since=3)
    C = value(2, until=3)
    C = value(3, since=3)

class H:
    e: E
"""

ENUM_FIELD_AFTER_NUMBERING = """
from enum import IntEnum
from protocol import field, packet, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = 1
    B = value(2, until=3)
    B = value(3, since=3)

@packet(id=1)
class P:
    e: E
    x: uint8 = field(since=2)
"""

ENUM_NARROW = """
from enum import IntEnum
from protocol import int16, packet, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, int16):
    A = 1
    B = value(2, until=3)
    B = value(3, since=3)

@packet(id=1)
class P:
    e: E
"""

ENUM_CONTAINERS = """
from enum import IntEnum
from protocol import packet, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = 1
    B = value(2, until=3)
    B = value(3, since=3)

@packet(id=1)
class P:
    many: list[E]
    keyed: dict[E, uint8]
    maybe: E | None
"""

ENUM_LITERAL_NUMBER = """
from enum import IntEnum
from typing import Literal
from protocol import packet, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = 1
    B = value(2, until=3)
    B = value(3, since=3)

@packet(id=1)
class P:
    tag: Literal[E.B]
"""

ENUM_WHEN_RENUMBERED = """
from enum import IntEnum
from protocol import field, packet, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = 1
    B = value(2, until=3)
    B = value(3, since=3)

@packet(id=1)
class P:
    e: E
    x: uint8 = field(when=lambda p: p.e == E.B)
"""

ENUM_TEST_RENUMBERED = """
from enum import IntEnum
from protocol import bitset, field, packet, sentinel, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = value(1, until=3)
    A = value(2, since=3)
    B = 4

class W(IntEnum, uint8):
    X = 1
    COUNT = sentinel()

@packet(id=1)
class P:
    bits: bitset[W.COUNT]
    x: uint8 = field(when=lambda p: p.bits.test(E.A))
"""

ENUM_WIDTH_ONLY = """
from enum import IntEnum
from protocol import bitset, packet, sentinel, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    X = 1
    COUNT = sentinel()
    Y = value(3, until=3)
    Y = value(4, since=3)

@packet(id=1)
class P:
    bits: bitset[E.COUNT]
"""

ENUM_NAMED_ALIAS = """
from enum import IntEnum
from protocol import field, packet, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class E(IntEnum, uint8):
    A = value(1, "old", until=3)
    A = value(1, "new", since=3)
    B = 2
    LATEST = B

@packet(id=1)
class P:
    e: E = field(type=str)
"""

PAIR_NAME_CODED_CHILD = """
from enum import IntEnum
from protocol import field, packet, type, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class B:
    class F(IntEnum, uint8):
        A = 1

    f: F

@type(cereal=False)
class B:
    class F(IntEnum, uint8):
        A = 1

    f: F = field(type=str)

@packet(id=1)
class P:
    b: B = field(cereal=False)
    c: B
"""

PAIR_SHARED_ENUM = """
from enum import IntEnum
from protocol import field, packet, type, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

class F(IntEnum, uint8):
    A = 1
    B = value(2, since=3)

@type(until=5)
class H:
    f: F

@type(cereal=False, until=5)
class H:
    f: F
    y: uint8

@packet(id=1, until=5)
class P:
    h: H = field(cereal=False)
"""

DEEP_CHILD_GAIN = """
from enum import IntEnum
from protocol import packet, type, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@type(until=3)
class N:
    class I:
        class F(IntEnum, uint8):
            A = 1

        f: F

    i: I

@type(since=3)
class N:
    class I:
        class F(IntEnum, uint8):
            A = 1
            B = value(2, since=4)

        f: F
        y: uint8

    i: I

@packet(id=1)
class P:
    n: N
"""

DEEP_SIBLING_GAIN = """
from enum import IntEnum
from protocol import packet, type, uint8, value
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@type(until=3)
class N:
    class J:
        x: uint8

    class I:
        class F(IntEnum, uint8):
            A = 1

        f: F
        j: N.J

    i: I

@type(since=3)
class N:
    class J:
        x: uint8
        y: uint8

    class I:
        class F(IntEnum, uint8):
            A = 1
            B = value(2, since=4)

        f: F
        j: N.J

    i: I

@packet(id=1)
class P:
    n: N
"""

DEEP_SHARED_CHAIN = """
from protocol import packet, type, uint8
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"

@type(until=3)
class N:
    class I:
        class U:
            class T:
                x: uint8

            t: T

        class S:
            t: N.I.U.T

        u: U
        s: S

    i: I

@type(since=3)
class N:
    class I:
        class U:
            class T:
                x: uint8

            t: T
            z: uint8

        class S:
            t: N.I.U.T

        u: U
        s: S

    i: I

@packet(id=1)
class P:
    n: N
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
        "values_v<::bedrock::protocol::D>{{\n    ::bedrock::protocol::D::A,\n"
        "    static_cast<::bedrock::protocol::D>(2),\n    static_cast<::bedrock::protocol::D>(3),\n"
        "    ::bedrock::protocol::D::Latest,\n}};"
    )

    names = 'names_v<::bedrock::protocol::D>{{\n    "a",\n    "old_deprecated",\n    "next",\n    "latest",\n}};'

    assert values in header
    assert names in header


def test_an_enum_with_a_deprecated_member_flags_each_reflected_member(generate):
    header = (generate({"a": DEPRECATED}) / "a.h").read_text()

    assert "deprecated_v<::bedrock::protocol::D>{{\n    false,\n    true,\n    true,\n    false,\n}};" in header


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


def test_a_list_read_caps_what_it_reserves_up_front(generate):
    out = generate({"a": LISTS})

    reserve = "        out.ids.reserve(detail::initialCapacity(static_cast<std::size_t>(*count0)));\n"
    assert reserve in (out / "a.cpp").read_text()


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


def test_a_struct_whose_enum_only_gains_a_member_is_one_model(generate):
    header = (generate({"a": ENUM_SPLIT}) / "a.h").read_text()

    assert header.count("\nstruct H {\n") == 1
    assert "::bedrock::protocol::v1::H" not in header
    assert "::bedrock::protocol::v3::H" not in header


def test_a_struct_whose_enum_only_gains_a_member_has_a_serializer_per_membership(generate):
    header = (generate({"a": ENUM_SPLIT}) / "a.h").read_text()

    assert header.count("struct Serializer<::bedrock::protocol::H, ") == 4
    assert (
        "template <>\nstruct Serializer<::bedrock::protocol::H, 1> {\n    static constexpr int since = 1;\n" in header
    )
    assert (
        "template <>\nstruct Serializer<::bedrock::protocol::H, 3> {\n    static constexpr int since = 3;\n" in header
    )


def test_a_struct_whose_enum_only_gains_a_member_stays_one_struct(generate):
    header = (generate({"a": ENUM_SPLIT}) / "a.h").read_text()

    assert header.count("\nstruct H {\n") == 1


def test_a_struct_whose_enum_is_renumbered_has_a_serializer_per_numbering(generate):
    header = (generate({"a": ENUM_RENUMBERED}) / "a.h").read_text()

    assert "template <>\nstruct Serializer<::bedrock::protocol::H, 1> {\n" in header
    assert "template <>\nstruct Serializer<::bedrock::protocol::H, 3> {\n" in header
    assert "::bedrock::protocol::v1::H" not in header


def test_a_renumbered_enum_is_one_enum_class_of_library_values(generate):
    header = (generate({"a": ENUM_RENUMBERED}) / "a.h").read_text()

    assert header.count("enum class E ") == 1
    assert "\nenum class E : std::uint8_t {\n    A = 1,\n    B = 3,\n};\n" in header
    assert "namespace v1" not in header


def test_a_renumbered_enum_is_selected_by_its_primary_definition_alone(generate):
    header = (generate({"a": ENUM_RENUMBERED}) / "a.h").read_text()

    assert "template <int V>\nstruct E_ { using type = ::bedrock::protocol::E; };\n" in header
    assert "struct E_<V>" not in header


@pytest.mark.parametrize(
    "line",
    [
        "std::array<NumberPair<::bedrock::protocol::E>, 1> encoded{{{3, 2}}}",
        "std::array<NumberPair<::bedrock::protocol::E>, 1> decoded{{{2, 3}}}",
        "std::array<std::uint8_t, 1> absent{{2}}",
        "std::array<std::uint8_t, 1> lossy{{3}}",
    ],
)
def test_a_numbering_holds_each_of_its_four_tables(generate, line):
    header = (generate({"a": ENUM_ASYMMETRIC}) / "a.h").read_text()

    assert "template <>\nstruct Numbering<::bedrock::protocol::E, 1> {\n" in header
    assert f"    static constexpr {line};\n" in header


def test_a_numbering_spells_an_empty_table_as_an_empty_array(generate):
    header = (generate({"a": ENUM_SPLIT}) / "a.h").read_text()

    assert "    static constexpr std::array<NumberPair<::bedrock::protocol::E>, 0> encoded{};\n" in header


def test_an_identity_numbering_emits_no_specialization(generate):
    header = (generate({"a": ENUM_SPLIT}) / "a.h").read_text()

    assert header.count("struct Numbering<") == 1
    assert "struct Numbering<::bedrock::protocol::E, 3>" not in header


def test_a_numbering_follows_the_reflection_of_its_enum_inside_detail(generate):
    header = (generate({"a": ENUM_RENUMBERED}) / "a.h").read_text()

    reflection = header.index("type_name_v<::bedrock::protocol::E>")
    specialization = header.index("struct Numbering<")
    assert reflection < specialization
    assert "}  // namespace detail" not in header[reflection:specialization]


def test_a_numbering_no_field_reaches_emits_no_specialization(generate):
    header = (generate({"a": ENUM_WIDTH_ONLY}) / "a.h").read_text()

    assert "struct Numbering<" not in header
    assert "detail/numbering.hpp" not in header


def test_an_enum_with_a_numbering_includes_the_numbering_runtime(generate):
    header = (generate({"a": ENUM_RENUMBERED}) / "a.h").read_text()

    assert "#include <bedrock/protocol/detail/numbering.hpp>\n" in header


def test_an_enum_without_a_numbering_does_not_include_the_numbering_runtime(generate):
    header = (generate({"a": ENUM_SHARED_VALUE}) / "a.h").read_text()

    assert "detail/numbering.hpp" not in header


def test_an_enum_gaining_members_is_one_block_holding_every_member(generate):
    header = (generate({"a": ENUM_SPLIT}) / "a.h").read_text()

    assert header.count("enum class E ") == 1
    assert "\nenum class E : std::uint8_t {\n    A = 1,\n    B = 2,\n};\n" in header
    assert "namespace v1 {\n\nenum class E" not in header


@pytest.mark.parametrize("table", ["values_v", "names_v", "schema_names_v", "type_name_v"])
def test_an_enum_gaining_members_has_one_reflection_table_of_each_kind(generate, table):
    header = (generate({"a": ENUM_SPLIT}) / "a.h").read_text()

    assert header.count(f" {table}<::bedrock::protocol::E>{{") == 1
    assert f" {table}<::bedrock::protocol::v1::E>{{" not in header


def test_an_enum_gaining_members_reflects_every_member(generate):
    header = (generate({"a": ENUM_SPLIT}) / "a.h").read_text()

    assert (
        "values_v<::bedrock::protocol::E>{{\n    ::bedrock::protocol::E::A,\n    ::bedrock::protocol::E::B,\n}};"
    ) in header
    assert 'schema_names_v<::bedrock::protocol::E>{{\n    "A",\n    "B",\n}};' in header


def test_an_enum_live_at_every_version_is_selected_by_its_primary_definition_alone(generate):
    header = (generate({"a": ENUM_SPLIT}) / "a.h").read_text()

    assert "template <int V>\nstruct E_ { using type = ::bedrock::protocol::E; };\n" in header
    assert "struct E_<V>" not in header


def test_an_enum_gaining_members_after_its_first_version_is_selected_by_one_partial(generate):
    header = (generate({"a": ENUM_LATE}) / "a.h").read_text()

    assert (
        "template <int V>\nstruct Z_;\n"
        "\n"
        "template <int V> requires (V >= 3)\n"
        "struct Z_<V> { using type = ::bedrock::protocol::Z; };\n"
    ) in header
    assert header.count("struct Z_<V>") == 1


def test_an_enum_gaining_members_before_it_ends_is_one_block_under_its_first_version(generate):
    header = (generate({"a": ENUM_ENDED}) / "a.h").read_text()

    assert header.count("enum class F ") == 1
    assert "namespace v1 {\n\nenum class F : std::uint8_t {\n    A = 1,\n    B = 2,\n};\n" in header


def test_an_enum_gaining_members_before_it_ends_is_selected_by_one_partial_over_its_run(generate):
    header = (generate({"a": ENUM_ENDED}) / "a.h").read_text()

    assert "template <int V> requires (V < 4)\nstruct F_<V> { using type = ::bedrock::protocol::v1::F; };\n" in header
    assert header.count("struct F_<V>") == 1


def test_members_sharing_a_value_are_ordered_newest_live_first_within_their_positions(generate):
    header = (generate({"a": ENUM_SHARED_VALUE}) / "a.h").read_text()

    assert "enum class E : std::int32_t {\n    New = 1,\n    Mid = 2,\n    Old = 1,\n    Alias = 2,\n};\n" in header


def test_the_newest_live_member_of_a_shared_value_is_the_first_reflected(generate):
    header = (generate({"a": ENUM_SHARED_VALUE}) / "a.h").read_text()

    assert (
        "values_v<::bedrock::protocol::E>{{\n"
        "    ::bedrock::protocol::E::New,\n"
        "    ::bedrock::protocol::E::Mid,\n"
        "    ::bedrock::protocol::E::Old,\n"
        "    ::bedrock::protocol::E::Alias,\n"
        "}};"
    ) in header
    assert 'names_v<::bedrock::protocol::E>{{\n    "new",\n    "mid",\n    "old",\n    "alias",\n}};' in header


def test_an_integer_coded_enum_field_at_an_identity_numbering_is_written_as_its_underlying_integer(generate):
    source = (generate({"a": ENUM_SPLIT}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::H, 3>::serialize(")
    assert "    stream.write<std::uint8_t>(value.e);\n" in body


def test_an_integer_coded_enum_field_at_an_identity_numbering_is_read_by_a_cast_of_the_integer(generate):
    source = (generate({"a": ENUM_SPLIT}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::H, 3>::deserialize(")
    assert (
        "        auto v = stream.read<std::uint8_t>();\n"
        '        if (!v) return stream.fail(v.error(), "e");\n'
        "        out.e = static_cast<::bedrock::protocol::E>(*v);\n"
    ) in body


def test_an_integer_coded_enum_field_at_a_numbering_is_written_through_its_number(generate):
    source = (generate({"a": ENUM_RENUMBERED}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::H, 1>::serialize(")
    assert (
        "    {\n"
        "        const auto n = detail::to_number<::bedrock::protocol::E, 1>(value.e);\n"
        '        if (!n) return stream.fail(n.error(), "e");\n'
        "        stream.write<std::uint8_t>(*n);\n"
        "    }\n"
    ) in body


def test_a_mapped_enum_field_names_the_since_of_its_numbering_not_of_its_struct(generate):
    source = (generate({"a": ENUM_FIELD_AFTER_NUMBERING}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 2>::serialize(")
    assert "        const auto n = detail::to_number<::bedrock::protocol::E, 1>(value.e);\n" in body


def test_an_integer_coded_enum_field_at_a_numbering_is_read_through_its_value(generate):
    source = (generate({"a": ENUM_RENUMBERED}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::H, 1>::deserialize(")
    assert (
        "        auto v = stream.read<std::uint8_t>();\n"
        '        if (!v) return stream.fail(v.error(), "e");\n'
        "        const auto e = detail::to_value<::bedrock::protocol::E, 1>(*v);\n"
        '        if (!e) return stream.fail(e.error(), "e");\n'
        "        out.e = *e;\n"
    ) in body


def test_a_narrowed_enum_number_is_checked_before_it_is_mapped(generate):
    source = (generate({"a": ENUM_NARROW}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 1>::deserialize(")
    assert (
        "        auto v = stream.readVarInt<std::int32_t>();\n"
        '        if (!v) return stream.fail(v.error(), "e");\n'
        "        const auto n = static_cast<std::int16_t>(*v);\n"
        '        if (static_cast<std::int32_t>(n) != *v) return stream.fail(Errc::out_of_range, "e");\n'
        "        const auto e = detail::to_value<::bedrock::protocol::E, 1>(n);\n"
    ) in body


def test_an_enum_inside_a_list_is_mapped(generate):
    source = (generate({"a": ENUM_CONTAINERS}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 1>::serialize(")
    assert "            const auto n = detail::to_number<::bedrock::protocol::E, 1>(e0);\n" in body


def test_an_enum_as_a_map_key_is_mapped(generate):
    source = (generate({"a": ENUM_CONTAINERS}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 1>::serialize(")
    assert "            const auto n = detail::to_number<::bedrock::protocol::E, 1>(k0);\n" in body


def test_an_enum_inside_an_optional_is_mapped(generate):
    source = (generate({"a": ENUM_CONTAINERS}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 1>::serialize(")
    assert "            const auto n = detail::to_number<::bedrock::protocol::E, 1>((*value.maybe));\n" in body


def test_an_enum_inside_a_list_reports_the_element_in_its_path(generate):
    source = (generate({"a": ENUM_CONTAINERS}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 1>::serialize(")
    assert "    for (std::size_t i0 = 0; const auto &e0 : value.many) {\n" in body
    assert '            if (!n) return stream.fail(n.error(), "many", i0);\n' in body


def test_a_literal_whose_number_differs_from_its_value_is_the_number(generate):
    source = (generate({"a": ENUM_LITERAL_NUMBER}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 1>::serialize(")
    assert "    stream.write<std::uint8_t>(2);\n" in body


def test_a_literal_whose_number_differs_from_its_value_is_compared_by_the_number(generate):
    source = (generate({"a": ENUM_LITERAL_NUMBER}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 1>::deserialize(")
    assert "        if (*v != static_cast<std::uint8_t>(2)) return stream.fail(Errc::unknown_value" in body


def test_a_literal_whose_number_is_its_value_stays_the_member(generate):
    source = (generate({"a": ENUM_LITERAL_NUMBER}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 3>::serialize(")
    assert "    stream.write<std::uint8_t>(::bedrock::protocol::E::B);\n" in body


@pytest.mark.parametrize("since", [1, 3])
def test_a_condition_on_a_renumbered_member_compares_its_library_value(generate, since):
    source = (generate({"a": ENUM_WHEN_RENUMBERED}) / "a.cpp").read_text()

    body = body_of(source, f"auto Serializer<::bedrock::protocol::P, {since}>::serialize(")
    assert "    if ((value.e) == (::bedrock::protocol::E::B)) {\n" in body


def test_a_tested_member_is_the_number_of_its_protocol_when_it_differs_from_its_value(generate):
    source = (generate({"a": ENUM_TEST_RENUMBERED}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 1>::serialize(")
    assert "    if (value.bits.test(static_cast<std::size_t>(1))) {\n" in body


def test_a_tested_member_is_the_member_when_its_number_is_its_value(generate):
    source = (generate({"a": ENUM_TEST_RENUMBERED}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 3>::serialize(")
    assert "    if (value.bits.test(static_cast<std::size_t>(::bedrock::protocol::E::A))) {\n" in body


def test_an_integer_coded_enum_field_has_no_membership_test(generate):
    source = (generate({"a": ENUM_SPLIT}) / "a.cpp").read_text()

    assert "enum_contains" not in source
    assert "enum_cast" not in source
    assert "unknown_value" not in source


def test_a_nested_enum_gaining_members_is_one_block_in_its_newest_holders_nested_namespace(generate):
    header = (generate({"a": SHARED_CHILD_GAIN}) / "a.h").read_text()

    assert header.count("enum class F ") == 1
    assert (
        "namespace N_nested {\n"
        "\n"
        "enum class F : std::uint8_t {\n"
        "    A = 1,\n"
        "    B = 2,\n"
        "};\n"
        "\n"
        "}  // namespace N_nested\n"
    ) in header
    assert "v1::N_nested" not in header


def test_a_nested_enum_gaining_members_is_declared_before_the_first_older_holder(generate):
    header = (generate({"a": SHARED_CHILD_GAIN}) / "a.h").read_text()

    assert header.index("namespace N_nested {\n\nenum class F ") < header.index("namespace v1 {\n")


def test_an_enum_two_levels_deep_is_declared_before_the_older_holder_that_uses_it(generate):
    header = (generate({"a": DEEP_CHILD_GAIN}) / "a.h").read_text()

    assert header.count("enum class F ") == 1
    assert header.index("namespace I_nested {\n\nenum class F ") < header.index("namespace v1 {\n")


def test_a_sibling_of_a_deep_enum_is_declared_before_the_holder_that_uses_it(generate):
    header = (generate({"a": DEEP_SIBLING_GAIN}) / "a.h").read_text()

    assert header.index("    std::uint8_t y{};\n") < header.index("    ::bedrock::protocol::N_nested::J j{};\n")


def test_a_deep_struct_is_declared_before_the_struct_that_uses_it(generate):
    header = (generate({"a": DEEP_SHARED_CHAIN}) / "a.h").read_text()

    assert header.index("\nstruct T {\n") < header.index("\nstruct S {\n")


def test_every_model_of_the_holder_aliases_the_one_nested_enum(generate):
    header = (generate({"a": SHARED_CHILD_GAIN}) / "a.h").read_text()

    assert header.count("    using F = ::bedrock::protocol::N_nested::F;\n") == 2
    assert header.count("    ::bedrock::protocol::N_nested::F f{};\n") == 2


def test_a_renamed_name_coded_member_is_written_by_its_old_name_at_the_protocol_that_names_it_so(generate):
    source = (generate({"a": ENUM_RENAMED_NAME}) / "a.cpp").read_text()

    assert 'naming_1_E_written{{\n    {::bedrock::protocol::E::A, "old"},\n}};' in source
    assert 'naming_3_E_written{{\n    {::bedrock::protocol::E::A, "new"},\n}};' in source


def test_a_renamed_name_coded_member_is_read_by_its_old_name_at_the_protocol_that_names_it_so(generate):
    source = (generate({"a": ENUM_RENAMED_NAME}) / "a.cpp").read_text()

    assert 'naming_1_E_read{{\n    {::bedrock::protocol::E::A, "old"},\n}};' in source
    assert 'naming_3_E_read{{\n    {::bedrock::protocol::E::A, "new"},\n}};' in source


def test_a_renamed_name_coded_enum_is_one_enum_class(generate):
    header = (generate({"a": ENUM_RENAMED_NAME}) / "a.h").read_text()

    assert header.count("enum class E ") == 1
    assert "namespace v1" not in header


def test_a_name_coded_enum_with_several_namings_has_a_serializer_per_naming(generate):
    header = (generate({"a": ENUM_RENAMED_NAME}) / "a.h").read_text()

    assert "template <>\nstruct Serializer<::bedrock::protocol::E, 1> {\n" in header
    assert "template <>\nstruct Serializer<::bedrock::protocol::E, 3> {\n" in header
    assert "template <int V> requires (V < 3)\nstruct Serializer<::bedrock::protocol::E, V> :" in header
    assert "template <int V> requires (V >= 3)\nstruct Serializer<::bedrock::protocol::E, V> :" in header


def test_a_name_coded_enum_with_several_namings_includes_the_naming_runtime(generate):
    header = (generate({"a": ENUM_RENAMED_NAME}) / "a.h").read_text()

    assert "#include <bedrock/protocol/detail/naming.hpp>\n" in header


def test_a_name_coded_enum_with_one_naming_does_not_include_the_naming_runtime(generate):
    header = (generate({"a": A}) / "a.h").read_text()

    assert "detail/naming.hpp" not in header


def test_a_naming_table_is_written_in_the_source_detail_namespace(generate):
    source = (generate({"a": ENUM_RENAMED_NAME}) / "a.cpp").read_text()

    assert source.index("namespace detail {") < source.index("naming_1_E_written")
    assert source.index("naming_3_E_read") < source.index("}  // namespace detail")
    assert source.index("}  // namespace detail") < source.index(
        "auto Serializer<::bedrock::protocol::E, 1>::serialize("
    )


def test_a_name_coded_member_gained_later_is_one_enum_class_holding_every_member(generate):
    header = (generate({"a": ENUM_NAME_GAINED}) / "a.h").read_text()

    assert "\nenum class E : std::uint8_t {\n    A = 1,\n    B = 2,\n};\n" in header
    assert "namespace v1" not in header


def test_a_name_coded_member_gained_later_has_no_row_in_the_naming_of_the_earlier_protocol(generate):
    source = (generate({"a": ENUM_NAME_GAINED}) / "a.cpp").read_text()

    assert 'naming_1_E_written{{\n    {::bedrock::protocol::E::A, "a"},\n}};' in source
    assert 'naming_1_E_read{{\n    {::bedrock::protocol::E::A, "a"},\n}};' in source


def test_a_value_without_a_row_fails_to_encode_by_name(generate):
    source = (generate({"a": ENUM_NAME_GAINED}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::E, 1>::serialize(")
    assert "    const auto name = detail::name_of(detail::naming_1_E_written, value);\n" in body
    assert "    if (!name) return std::unexpected(Errc::unknown_value);\n" in body


def test_a_name_without_a_row_fails_to_decode_by_name(generate):
    source = (generate({"a": ENUM_NAME_GAINED}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::E, 1>::deserialize(")
    assert "    const auto value = detail::value_of(detail::naming_1_E_read, *v);\n" in body
    assert "    if (!value) return std::unexpected(Errc::unknown_value);\n" in body


def test_an_alias_of_a_name_coded_member_decodes_to_its_target(generate):
    source = (generate({"a": ENUM_NAMED_ALIAS}) / "a.cpp").read_text()

    read = source.partition("naming_3_E_read{{")[2].partition("}};")[0]
    assert '    {::bedrock::protocol::E::B, "b"},\n' in read
    assert '    {::bedrock::protocol::E::B, "latest"},\n' in read


def test_an_alias_of_a_name_coded_member_is_written_by_its_alias_name_in_one_row(generate):
    source = (generate({"a": ENUM_NAMED_ALIAS}) / "a.cpp").read_text()

    written = source.partition("naming_3_E_written{{")[2].partition("}};")[0]
    assert written.count("::bedrock::protocol::E::B,") == 1
    assert '    {::bedrock::protocol::E::B, "latest"},\n' in written


def test_a_child_call_of_a_name_coded_enum_names_the_since_of_its_naming(generate):
    source = (generate({"a": ENUM_RENAMED_NAME}) / "a.cpp").read_text()

    older = body_of(source, "auto Serializer<::bedrock::protocol::P, 1>::serialize(")
    newer = body_of(source, "auto Serializer<::bedrock::protocol::P, 3>::serialize(")
    assert "        auto r = Serializer<::bedrock::protocol::E, 1>::serialize(stream, value.e);\n" in older
    assert "        auto r = Serializer<::bedrock::protocol::E, 3>::serialize(stream, value.e);\n" in newer


def test_a_literal_of_a_derived_member_writes_the_number_of_its_protocol_when_the_value_differs(generate):
    source = (generate({"a": ENUM_DERIVED_MEMBER}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 1>::serialize(")
    assert "    stream.write<std::uint8_t>(1);\n" in body


def test_a_literal_of_a_derived_member_is_the_member_when_the_value_is_the_number(generate):
    source = (generate({"a": ENUM_DERIVED_MEMBER}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::P, 3>::serialize(")
    assert "    stream.write<std::uint8_t>(::bedrock::protocol::E::Latest);\n" in body


def test_an_alias_follows_its_target_in_the_reflection_tables(generate):
    header = (generate({"a": ENUM_DERIVED_MEMBER}) / "a.h").read_text()

    assert (
        "values_v<::bedrock::protocol::E>{{\n"
        "    ::bedrock::protocol::E::A,\n"
        "    ::bedrock::protocol::E::B,\n"
        "    ::bedrock::protocol::E::Latest,\n"
        "}};"
    ) in header


def test_a_unioned_enum_marks_a_deprecated_member_in_its_deprecated_table(generate):
    header = (generate({"a": ENUM_DEPRECATED_GAIN}) / "a.h").read_text()

    assert "deprecated_v<::bedrock::protocol::D>{{\n    false,\n    true,\n    false,\n}};" in header


def test_a_unioned_enum_reflects_a_deprecated_member_by_its_number(generate):
    header = (generate({"a": ENUM_DEPRECATED_GAIN}) / "a.h").read_text()

    assert (
        "values_v<::bedrock::protocol::D>{{\n"
        "    ::bedrock::protocol::D::A,\n"
        "    static_cast<::bedrock::protocol::D>(2),\n"
        "    ::bedrock::protocol::D::B,\n"
        "}};"
    ) in header


def test_a_name_coded_enum_nested_in_both_forms_of_a_pair_has_a_declared_serializer(generate):
    header = (generate({"a": PAIR_NAME_CODED_CHILD}) / "a.h").read_text()

    assert "template <>\nstruct Serializer<::bedrock::protocol::B_nested::F, 1> {\n" in header


def test_a_name_coded_enum_nested_in_both_forms_of_a_pair_has_a_defined_serializer(generate):
    source = (generate({"a": PAIR_NAME_CODED_CHILD}) / "a.cpp").read_text()

    assert "\nauto Serializer<::bedrock::protocol::B_nested::F, 1>::serialize(" in source
    assert "\nauto Serializer<::bedrock::protocol::B_nested::F, 1>::deserialize(" in source


def test_an_enum_shared_by_both_forms_of_a_pair_is_declared_once(generate):
    header = (generate({"a": PAIR_SHARED_ENUM}) / "a.h").read_text()

    assert header.count("enum class F ") == 1
    assert "\nenum class F : std::uint8_t {\n    A = 1,\n    B = 2,\n};\n" in header


def test_an_enum_shared_by_both_forms_of_a_pair_is_the_member_type_of_each(generate):
    header = (generate({"a": PAIR_SHARED_ENUM}) / "a.h").read_text()

    assert header.count("    ::bedrock::protocol::F f{};\n") == 2


def test_a_name_coded_enum_with_one_shape_keeps_its_membership_check_on_write(generate):
    source = (generate({"a": A}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::E, 1>::serialize(")
    assert "    if (!enum_contains(value)) return std::unexpected(Errc::unknown_value);\n" in body


def test_a_name_coded_enum_with_one_shape_rejects_an_unknown_name_on_read(generate):
    source = (generate({"a": A}) / "a.cpp").read_text()

    body = body_of(source, "auto Serializer<::bedrock::protocol::E, 1>::deserialize(")
    assert (
        "    const auto value = enum_cast<::bedrock::protocol::E>(*v);\n"
        "    if (!value) return std::unexpected(Errc::unknown_value);\n"
    ) in body


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
