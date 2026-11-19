import bedrock_protocol as bp


def test_an_alias_crosses_as_its_primitive():
    assert type(bp.RemoveActorPacket().entity_id) is int


def test_a_default_alias_is_zero():
    assert bp.RemoveActorPacket().entity_id == 0


def test_a_signed_alias_keeps_its_sign_in_the_encoding(protocol):
    packet = bp.RemoveActorPacket(entity_id=-3)
    assert protocol.decode(bp.RemoveActorPacket, protocol.encode(packet)) == packet
