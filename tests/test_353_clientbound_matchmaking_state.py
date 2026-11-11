import pytest

from bedrock_protocol import v2193, v2225

WITHOUT_OPTIONS = v2225.ClientboundMatchmakingStatePacket(
    state=v2225.MatchmakingState.MATCHMAKING,
    destination_name="lobby",
)
WITH_OPTIONS = v2225.ClientboundMatchmakingStatePacket(
    state=v2225.MatchmakingState.PLAYER_LEFT_PARTY,
    destination_name="",
    options=v2225.MatchmakingStateOptions(triggering_player_name="Alex", triggered_by_local_player=None),
)


def test_clientbound_matchmaking_state_is_packet_353_from_2225():
    assert v2225.PACKETS[353] is v2225.ClientboundMatchmakingStatePacket


def test_clientbound_matchmaking_state_is_absent_at_2193():
    assert 353 not in v2193.PACKETS


@pytest.mark.parametrize(
    ("packet", "size"),
    [
        pytest.param(WITHOUT_OPTIONS, 8, id="v2225-without-options"),
        pytest.param(WITH_OPTIONS, 10, id="v2225-with-options"),
    ],
)
def test_clientbound_matchmaking_state_encodes_to_its_size(packet, size):
    assert len(bytes(packet)) == size


@pytest.mark.parametrize(
    "packet",
    [pytest.param(WITHOUT_OPTIONS, id="v2225-without-options"), pytest.param(WITH_OPTIONS, id="v2225-with-options")],
)
def test_clientbound_matchmaking_state_round_trips(packet):
    assert v2225.ClientboundMatchmakingStatePacket.from_bytes(bytes(packet)) == packet
