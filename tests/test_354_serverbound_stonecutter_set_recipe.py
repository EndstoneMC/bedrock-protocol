from bedrock_protocol import v2193, v2225

PACKET = v2225.ServerboundStonecutterSetRecipePacket(container_id=v2225.ContainerID.FIRST, recipe_index=7)
# TODO: confirm against BDS: gophertunnel stops at 2168 and cannot marshal this packet; the bytes follow the r26_u6 dump
ENCODED = bytes.fromhex("010e")


def test_serverbound_stonecutter_set_recipe_is_packet_354_from_2225():
    assert v2225.PACKETS[354] is v2225.ServerboundStonecutterSetRecipePacket


def test_serverbound_stonecutter_set_recipe_is_absent_at_2193():
    assert 354 not in v2193.PACKETS


def test_serverbound_stonecutter_set_recipe_encodes_to_its_bytes():
    assert bytes(PACKET) == ENCODED


def test_serverbound_stonecutter_set_recipe_decodes_from_its_bytes():
    assert v2225.ServerboundStonecutterSetRecipePacket.from_bytes(ENCODED) == PACKET
