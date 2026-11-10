def test_an_alias_crosses_as_its_primitive(protocol):
    assert protocol.RemoveActorPacket.__annotations__["entity_id"] is int


def test_a_default_alias_is_zero(protocol):
    assert protocol.RemoveActorPacket().entity_id == 0


def test_a_signed_alias_keeps_its_sign_on_the_wire(protocol):
    packet = protocol.RemoveActorPacket(entity_id=-3)
    assert protocol.RemoveActorPacket.from_bytes(bytes(packet)) == packet
