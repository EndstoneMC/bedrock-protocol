from bedrock_protocol import v2225

PACKET = v2225.ServerboundStonecutterSetRecipePacket(container_id=v2225.ContainerID.FIRST, recipe_index=7)


def test_serverbound_stonecutter_set_recipe_encodes_to_two_bytes():
    assert len(bytes(PACKET)) == 2


def test_serverbound_stonecutter_set_recipe_round_trips():
    assert v2225.ServerboundStonecutterSetRecipePacket.from_bytes(bytes(PACKET)) == PACKET
