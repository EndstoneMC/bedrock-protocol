from bedrock_protocol import v2225

PACKET = v2225.ServerboundCursorItemDragPacket(state=v2225.CursorItemDragState.STOP)


def test_serverbound_cursor_item_drag_encodes_to_one_byte():
    assert len(bytes(PACKET)) == 1


def test_serverbound_cursor_item_drag_round_trips():
    assert v2225.ServerboundCursorItemDragPacket.from_bytes(bytes(PACKET)) == PACKET
