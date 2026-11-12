from bedrock_protocol import v2225

EMPTY = b""


def test_serverbound_matchmaking_cancel_has_an_empty_body():
    assert bytes(v2225.ServerboundMatchmakingCancelPacket()) == EMPTY


def test_serverbound_matchmaking_cancel_decodes_from_an_empty_body():
    assert v2225.ServerboundMatchmakingCancelPacket.from_bytes(EMPTY) == v2225.ServerboundMatchmakingCancelPacket()
