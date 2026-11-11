from bedrock_protocol import v2193, v2225

EMPTY = b""


def test_serverbound_matchmaking_cancel_is_packet_356_from_2225():
    assert v2225.PACKETS[356] is v2225.ServerboundMatchmakingCancelPacket


def test_serverbound_matchmaking_cancel_is_absent_at_2193():
    assert 356 not in v2193.PACKETS


def test_serverbound_matchmaking_cancel_has_an_empty_body():
    assert bytes(v2225.ServerboundMatchmakingCancelPacket()) == EMPTY


def test_serverbound_matchmaking_cancel_decodes_from_an_empty_body():
    assert v2225.ServerboundMatchmakingCancelPacket.from_bytes(EMPTY) == v2225.ServerboundMatchmakingCancelPacket()
