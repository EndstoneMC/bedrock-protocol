import os

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
        os.utime(path, ns=(1, 1))

    main([str(tmp_path / "protocol"), "--out", str(tmp_path / "out")])

    assert {path.stat().st_mtime_ns for path in out.iterdir()} == {1}


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


def test_a_deprecated_member_reflects_its_number_and_wire_name(generate):
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
        os.utime(path, ns=(1, 1))
    (tmp_path / "protocol/b.py").write_text(
        'package = "bedrock.protocol"\njava_package = "dev.endstone.protocol"\nclass B:\n    x: Missing\n'
    )

    with pytest.raises(SystemExit, match=r"bpc: .*Missing"):
        main([str(tmp_path / "protocol"), "--out", str(tmp_path / "out")])

    assert {path.name: path.read_bytes() for path in out.iterdir()} == before
    assert {path.stat().st_mtime_ns for path in out.iterdir()} == {1}


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
