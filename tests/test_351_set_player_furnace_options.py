import pytest

from bedrock_protocol import v2168, v2193


def test_set_player_furnace_options_is_packet_351_from_2193():
    assert v2193.PACKETS[351] is v2193.SetPlayerFurnaceOptionsPacket


def test_set_player_furnace_options_is_absent_at_2168():
    assert 351 not in v2168.PACKETS


@pytest.fixture
def packet():
    return v2193.SetPlayerFurnaceOptionsPacket(
        furnace_type=v2193.SetPlayerFurnaceOptionsPacket.FurnaceType.SMOKER,
        furnace_options=v2193.FurnaceOptions(
            left_furnace_tab=v2193.FurnaceLeftTabIndex.INVENTORY,
            filtering=True,
            layout=v2193.FurnaceLayout.DEFAULT,
        ),
    )


def test_set_player_furnace_options_encodes_to_four_bytes(packet):
    assert len(bytes(packet)) == 4


def test_set_player_furnace_options_round_trips(packet):
    assert v2193.SetPlayerFurnaceOptionsPacket.from_bytes(bytes(packet)) == packet
