import pytest

from bedrock_protocol import v786, v940, v975, v1001, v2168, v2193, v2225


def test_a_snapshot_packet_resolves_to_the_type_of_its_first_bound_version():
    assert v975.PACKETS[74] is v786.BossEventPacket


def test_a_packet_changed_at_1001_resolves_to_its_own_type():
    assert v1001.PACKETS[74] is v1001.BossEventPacket


def test_a_packet_unchanged_since_1001_resolves_to_that_type_at_2168():
    assert v2168.PACKETS[74] is v1001.BossEventPacket


def test_a_packet_never_redeclared_resolves_to_one_type_across_versions():
    assert v975.PACKETS[1] is v2225.LoginPacket


@pytest.mark.parametrize("packet_id", [0, 999])
def test_an_unmodelled_id_is_absent(packet_id):
    assert packet_id not in v1001.PACKETS


@pytest.mark.parametrize(
    ("version", "packet_id"),
    [
        pytest.param(v975, 348, id="v975-348"),
        pytest.param(v940, 345, id="v940-345"),
        pytest.param(v2193, 353, id="v2193-353"),
        pytest.param(v2193, 356, id="v2193-356"),
        pytest.param(v2193, 357, id="v2193-357"),
    ],
)
def test_a_packet_is_absent_before_the_version_that_adds_it(version, packet_id):
    assert packet_id not in version.PACKETS


@pytest.mark.parametrize(
    ("version", "packet_id"),
    [
        pytest.param(v1001, 348, id="v1001-348"),
        pytest.param(v975, 345, id="v975-345"),
        pytest.param(v2225, 353, id="v2225-353"),
        pytest.param(v2225, 356, id="v2225-356"),
        pytest.param(v2225, 360, id="v2225-360"),
    ],
)
def test_a_packet_is_present_at_the_version_that_adds_it(version, packet_id):
    assert packet_id in version.PACKETS


def test_the_packet_id_range_ends_at_361_in_2225():
    assert v2225.MinecraftPacketIds.END_ID == 361
