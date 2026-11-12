from bedrock_protocol import v2193, v2225

PACKET = v2225.ClientboundStonecutterSetRecipePacket(player_id=5, container_id=v2225.ContainerID.FIRST, recipe_index=7)


def test_clientbound_stonecutter_set_recipe_is_packet_355_from_2225():
    assert v2225.packets[355] is v2225.ClientboundStonecutterSetRecipePacket


def test_clientbound_stonecutter_set_recipe_is_absent_at_2193():
    assert 355 not in v2193.packets


def test_clientbound_stonecutter_set_recipe_encodes_to_three_bytes():
    assert len(bytes(PACKET)) == 3


def test_clientbound_stonecutter_set_recipe_round_trips():
    assert v2225.ClientboundStonecutterSetRecipePacket.from_bytes(bytes(PACKET)) == PACKET
