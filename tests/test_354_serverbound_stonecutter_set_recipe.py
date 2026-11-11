from bedrock_protocol import v2193, v2225

PACKET = v2225.ServerboundStonecutterSetRecipePacket(container_id=v2225.ContainerID.FIRST, recipe_index=7)


def test_serverbound_stonecutter_set_recipe_is_packet_354_from_2225():
    assert v2225.PACKETS[354] is v2225.ServerboundStonecutterSetRecipePacket


def test_serverbound_stonecutter_set_recipe_is_absent_at_2193():
    assert 354 not in v2193.PACKETS


def test_serverbound_stonecutter_set_recipe_encodes_to_two_bytes():
    assert len(bytes(PACKET)) == 2


def test_serverbound_stonecutter_set_recipe_round_trips():
    assert v2225.ServerboundStonecutterSetRecipePacket.from_bytes(bytes(PACKET)) == PACKET
