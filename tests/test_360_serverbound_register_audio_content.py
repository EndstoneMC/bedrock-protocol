from bedrock_protocol import v2193, v2225

PACKET = v2225.ServerboundRegisterAudioContentPacket(
    registrations=[
        v2225.AudioContentRegistrationEntry(
            audio_content_id="id",
            shared_metadata=v2225.SignedAudioContent(compact_jwt="s"),
            server_content=v2225.SignedAudioContent(compact_jwt="v"),
            playback_content=v2225.SignedAudioContent(compact_jwt="p"),
        )
    ]
)
ENCODED = bytes.fromhex("0102" + "6964" + "0173" + "0176" + "0170")


def test_serverbound_register_audio_content_is_packet_360_from_2225():
    assert v2225.PACKETS[360] is v2225.ServerboundRegisterAudioContentPacket


def test_serverbound_register_audio_content_is_absent_at_2193():
    assert 360 not in v2193.PACKETS


def test_serverbound_register_audio_content_encodes_to_its_bytes():
    assert bytes(PACKET) == ENCODED


def test_serverbound_register_audio_content_decodes_from_its_bytes():
    assert v2225.ServerboundRegisterAudioContentPacket.from_bytes(ENCODED) == PACKET
