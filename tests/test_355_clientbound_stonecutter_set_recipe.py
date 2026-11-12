from bedrock_protocol import v2225

PACKET = v2225.ClientboundStonecutterSetRecipePacket(
    player_unique_id=5, container_id=v2225.ContainerID.FIRST, recipe_index=7
)


def test_clientbound_stonecutter_set_recipe_encodes_to_three_bytes():
    assert len(bytes(PACKET)) == 3


def test_clientbound_stonecutter_set_recipe_round_trips():
    assert v2225.ClientboundStonecutterSetRecipePacket.from_bytes(bytes(PACKET)) == PACKET
