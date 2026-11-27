import pytest

import bedrock_protocol as bp
from bedrock_protocol import (
    v622,
    v630,
    v649,
    v662,
    v671,
    v685,
    v686,
    v712,
    v729,
    v776,
    v844,
    v859,
    v898,
    v975,
    v1001,
    v2168,
    v2225,
)


def test_a_snapshot_packet_resolves_to_the_type_of_its_first_bound_version():
    assert v975.packets[74] is v776.BossEventPacket


def test_a_packet_unchanged_since_1001_resolves_to_that_type_at_2168():
    assert v2168.packets[74] is v1001.BossEventPacket


def test_a_packet_never_redeclared_resolves_to_one_type_across_versions():
    assert v975.packets[1] is bp.LoginPacket


@pytest.mark.parametrize("version", [v729, v844], ids=lambda module: module.__name__)
def test_a_packet_whose_forms_differ_only_in_an_enums_members_resolves_to_one_class(version):
    packet = bp.PacketViolationWarningPacket
    assert version.packets[packet.ID] is packet


@pytest.mark.parametrize("version", [v729, v1001], ids=lambda module: module.__name__)
def test_a_packet_whose_enum_changes_its_numbers_resolves_to_one_class(version):
    packet = bp.SetLastHurtByPacket
    assert version.packets[packet.ID] is packet


@pytest.mark.parametrize(
    ("version", "end_id"),
    [
        pytest.param(v622, 306, id="v622"),
        pytest.param(v630, 308, id="v630"),
        pytest.param(v649, 309, id="v649"),
        pytest.param(v662, 309, id="v662"),
        pytest.param(v671, 309, id="v671"),
        pytest.param(v685, 310, id="v685"),
        pytest.param(v686, 311, id="v686"),
        pytest.param(v712, 316, id="v712"),
        pytest.param(v844, 330, id="v844"),
        pytest.param(v859, 332, id="v859"),
        pytest.param(v898, 333, id="v898"),
        pytest.param(v975, 348, id="v975"),
        pytest.param(v1001, 351, id="v1001"),
        pytest.param(v2225, 361, id="v2225"),
    ],
)
def test_the_highest_packet_id_sits_just_below_the_end_marker(version, end_id):
    assert max(version.packets) == end_id - 1
