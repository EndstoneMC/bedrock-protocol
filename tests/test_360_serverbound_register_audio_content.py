from bedrock_protocol import v2225

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


def test_serverbound_register_audio_content_encodes_to_ten_bytes():
    assert len(bytes(PACKET)) == 10


def test_serverbound_register_audio_content_round_trips():
    assert v2225.ServerboundRegisterAudioContentPacket.from_bytes(bytes(PACKET)) == PACKET
