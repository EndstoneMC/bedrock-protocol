from bedrock_protocol import v2193, v2225

# TODO: confirm against BDS: gophertunnel stops at 2168 and cannot marshal this packet; the bytes follow the r26_u6 dump
DISMOUNT = bytes.fromhex("0a00")
DISMOUNT_PACKET = v2225.SetPassengerOfBlockPacket(passenger=5)
MOUNT = v2225.SetPassengerOfBlockPacket(
    passenger=5,
    passenger_of_block_data=v2225.PassengerOfBlockArguments(
        block_pos=v2225.BlockPos(x=-1, y=64, z=2),
        offset=v2225.Vec3(x=0.5, y=0.25, z=0.5),
        rotation=180.0,
        rotation_limit=30.0,
        emote_type=v2225.PassengerOfBlockArguments.EmoteType.STANDING,
    ),
)


def test_set_passenger_of_block_is_packet_357_from_2225():
    assert v2225.PACKETS[357] is v2225.SetPassengerOfBlockPacket


def test_set_passenger_of_block_is_absent_at_2193():
    assert 357 not in v2193.PACKETS


def test_set_passenger_of_block_encodes_a_dismount_to_its_bytes():
    assert bytes(DISMOUNT_PACKET) == DISMOUNT


def test_set_passenger_of_block_decodes_a_dismount_from_its_bytes():
    assert v2225.SetPassengerOfBlockPacket.from_bytes(DISMOUNT) == DISMOUNT_PACKET


def test_set_passenger_of_block_mounted_body_is_twenty_seven_bytes():
    assert len(bytes(MOUNT)) == 27


def test_set_passenger_of_block_round_trips_a_mount():
    assert v2225.SetPassengerOfBlockPacket.from_bytes(bytes(MOUNT)) == MOUNT
