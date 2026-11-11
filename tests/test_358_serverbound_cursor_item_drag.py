from bedrock_protocol import v2193, v2225

PACKET = v2225.ServerboundCursorItemDragPacket(state=v2225.CursorItemDragState.STOP)
# TODO: confirm against BDS: gophertunnel stops at 2168 and cannot marshal this packet; the bytes follow the r26_u6 dump
ENCODED = bytes.fromhex("01")


def test_serverbound_cursor_item_drag_is_packet_358_from_2225():
    assert v2225.PACKETS[358] is v2225.ServerboundCursorItemDragPacket


def test_serverbound_cursor_item_drag_is_absent_at_2193():
    assert 358 not in v2193.PACKETS


def test_serverbound_cursor_item_drag_encodes_to_its_bytes():
    assert bytes(PACKET) == ENCODED


def test_serverbound_cursor_item_drag_decodes_from_its_bytes():
    assert v2225.ServerboundCursorItemDragPacket.from_bytes(ENCODED) == PACKET
