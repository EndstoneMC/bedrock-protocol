import importlib
import json
from pathlib import Path

import pytest

from bedrock_protocol import v786, v844, v859, v898, v975, v1001, v2168, v2225

PACKET_IDS = json.loads((Path(__file__).parent / "packet_ids.json").read_text())

ROWS = PACKET_IDS["packets"] + PACKET_IDS["unlisted"]

NAMES = [
    pytest.param(version, entry["id"], entry["name"], id=f"v{version}-{entry['id']}")
    for entry in ROWS
    for version in entry["versions"]
]


def test_a_snapshot_packet_resolves_to_the_type_of_its_first_bound_version():
    assert v975.packets[74] is v786.BossEventPacket


def test_a_packet_unchanged_since_1001_resolves_to_that_type_at_2168():
    assert v2168.packets[74] is v1001.BossEventPacket


def test_a_packet_never_redeclared_resolves_to_one_type_across_versions():
    assert v975.packets[1] is v2225.LoginPacket


@pytest.mark.parametrize(("version", "packet_id", "name"), NAMES)
def test_a_packet_id_names_the_listed_packet(version, packet_id, name):
    assert importlib.import_module(f"bedrock_protocol.v{version}").packets[packet_id].__name__ == name


def test_a_version_binds_exactly_the_listed_packet_ids(protocol):
    version = int(protocol.__name__.rpartition(".")[2].removeprefix("v"))
    assert sorted(protocol.packets) == sorted(entry["id"] for entry in ROWS if version in entry["versions"])


@pytest.mark.parametrize(
    ("version", "end_id"),
    [
        pytest.param(v844, 330, id="v844"),
        pytest.param(v859, 332, id="v859"),
        pytest.param(v898, 333, id="v898"),
        pytest.param(v975, 348, id="v975"),
        pytest.param(v1001, 351, id="v1001"),
        pytest.param(v2225, 361, id="v2225"),
    ],
)
def test_the_packet_id_range_ends_at_the_end_marker(version, end_id):
    assert end_id == version.MinecraftPacketIds.END_ID
