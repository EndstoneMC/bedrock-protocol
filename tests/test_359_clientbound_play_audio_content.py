from bedrock_protocol import v2193, v2225

SOUND = v2225.PlaySoundPacket(name="record.cat", pos=v2225.BlockPos(x=1, y=2, z=3), volume=1.0, pitch=1.0)
PACKET = v2225.ClientboundPlayAudioContentPacket(
    shared_metadata=v2225.SignedAudioContent(compact_jwt="a.b.c"),
    playback_content=v2225.SignedAudioContent(compact_jwt="d.e.f"),
    playback_type=v2225.AudioContentPlaybackType.MUSIC,
    play_sound=SOUND,
)
# TODO: confirm against BDS: gophertunnel stops at 2168 and cannot marshal this packet; the bytes follow the r26_u6 dump
HEAD = bytes.fromhex("05612e622e6305642e652e66056d75736963")


def test_clientbound_play_audio_content_is_packet_359_from_2225():
    assert v2225.PACKETS[359] is v2225.ClientboundPlayAudioContentPacket


def test_clientbound_play_audio_content_is_absent_at_2193():
    assert 359 not in v2193.PACKETS


def test_clientbound_play_audio_content_carries_the_play_sound_body_inline():
    assert bytes(PACKET) == HEAD + bytes(SOUND)


def test_clientbound_play_audio_content_decodes_from_its_bytes():
    assert v2225.ClientboundPlayAudioContentPacket.from_bytes(HEAD + bytes(SOUND)) == PACKET
