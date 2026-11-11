import pytest

from bedrock_protocol import v2193, v2225


def test_clientbound_matchmaking_state_is_packet_353_from_2225():
    assert v2225.PACKETS[353] is v2225.ClientboundMatchmakingStatePacket


def test_clientbound_matchmaking_state_is_absent_at_2193():
    assert 353 not in v2193.PACKETS


GOLDENS = [
    pytest.param(
        v2225.ClientboundMatchmakingStatePacket(
            state=v2225.MatchmakingState.MATCHMAKING,
            destination_name="lobby",
        ),
        bytes.fromhex("0105" + "6c6f626279" + "00"),
        id="v2225-without-options",
    ),
    pytest.param(
        v2225.ClientboundMatchmakingStatePacket(
            state=v2225.MatchmakingState.PLAYER_LEFT_PARTY,
            destination_name="",
            options=v2225.MatchmakingStateOptions(triggering_player_name="Alex", triggered_by_local_player=None),
        ),
        bytes.fromhex("0400" + "0101" + "04416c6578" + "00"),
        id="v2225-with-options",
    ),
]


@pytest.mark.parametrize(("packet", "encoded"), GOLDENS)
def test_clientbound_matchmaking_state_encodes_to_its_bytes(packet, encoded):
    assert bytes(packet) == encoded


@pytest.mark.parametrize(("packet", "encoded"), GOLDENS)
def test_clientbound_matchmaking_state_decodes_from_its_bytes(packet, encoded):
    assert v2225.ClientboundMatchmakingStatePacket.from_bytes(encoded) == packet
