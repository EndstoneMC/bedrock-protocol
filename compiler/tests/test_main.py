import os

import pytest

from bedrock_protocol_compiler.__main__ import main

A = """
from enum import IntEnum
from protocol import field, packet, type, uint8
package = "bedrock.protocol"

class E(IntEnum, uint8):
    X = 1

@packet(id=1)
class P:
    e: E = field(type=str)
"""

B = """
from protocol import type, uint8
package = "bedrock.protocol"

class B:
    x: uint8
"""


C = """
from protocol import packet, uint8
package = "bedrock.protocol"

@packet(id=2)
class Q:
    x: uint8
"""


BITSET = """
from enum import IntEnum
from protocol import bitset, type, uint8
package = "bedrock.protocol"

class E(IntEnum, uint8):
    A = 1
    B = 2
    COUNT = B

class P:
    x: bitset[E.COUNT]
"""


@pytest.fixture
def generate(build_package, tmp_path):
    def run(modules: dict[str, str]):
        build_package(modules)
        main([str(tmp_path / "protocol"), "--out", str(tmp_path / "out")])
        return tmp_path / "out/bedrock/protocol"

    return run


def test_a_header_and_a_source_per_module_and_a_version_header(generate):
    out = generate({"a": A, "b": B})

    assert sorted(path.name for path in out.iterdir()) == ["a.cpp", "a.h", "b.cpp", "b.h", "packets.h", "version.hpp"]


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

    assert sorted(path.name for path in out.iterdir()) == ["a.cpp", "a.h", "packets.h", "version.hpp"]


def test_a_schema_error_exits_with_its_message(build_package, tmp_path):
    build_package({"a": B})
    (tmp_path / "protocol/a.py").write_text('package = "bedrock.protocol"\nclass A:\n    x: Missing\n')

    with pytest.raises(SystemExit, match=r"bpc: .*Missing"):
        main([str(tmp_path / "protocol"), "--out", str(tmp_path / "out")])


def test_a_bitset_width_may_name_a_derived_member(generate):
    out = generate({"a": BITSET})

    assert (out / "a.h").exists()


def test_a_schema_error_leaves_the_output_tree_untouched(generate, tmp_path):
    out = generate({"a": A, "b": B})
    before = {path.name: path.read_bytes() for path in out.iterdir()}
    for path in out.iterdir():
        os.utime(path, ns=(1, 1))
    (tmp_path / "protocol/b.py").write_text('package = "bedrock.protocol"\nclass B:\n    x: Missing\n')

    with pytest.raises(SystemExit, match=r"bpc: .*Missing"):
        main([str(tmp_path / "protocol"), "--out", str(tmp_path / "out")])

    assert {path.name: path.read_bytes() for path in out.iterdir()} == before
    assert {path.stat().st_mtime_ns for path in out.iterdir()} == {1}


def test_packets_h_names_every_packet_of_every_module(generate):
    out = generate({"a": A, "c": C})

    registry = (out / "packets.h").read_text()
    assert "struct packet_of<V, 1>" in registry
    assert "struct packet_of<V, 2>" in registry
    assert "packet_of" not in (out / "a.h").read_text()
