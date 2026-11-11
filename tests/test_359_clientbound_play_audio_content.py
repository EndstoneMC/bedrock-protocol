from bedrock_protocol import v2193, v2225

SOUND = v2225.PlaySoundPacket(name="record.cat", pos=v2225.BlockPos(x=1, y=2, z=3), volume=1.0, pitch=1.0)
PACKET = v2225.ClientboundPlayAudioContentPacket(
    shared_metadata=v2225.SignedAudioContent(compact_jwt="a.b.c"),
    playback_content=v2225.SignedAudioContent(compact_jwt="d.e.f"),
    playback_type=v2225.AudioContentPlaybackType.MUSIC,
    play_sound=SOUND,
)


def test_clientbound_play_audio_content_is_packet_359_from_2225():
    assert v2225.PACKETS[359] is v2225.ClientboundPlayAudioContentPacket


def test_clientbound_play_audio_content_is_absent_at_2193():
    assert 359 not in v2193.PACKETS


def test_clientbound_play_audio_content_is_forty_four_bytes():
    assert len(bytes(PACKET)) == 44


def test_clientbound_play_audio_content_ends_with_the_play_sound_body():
    assert bytes(PACKET).endswith(bytes(SOUND))


def test_clientbound_play_audio_content_round_trips():
    assert v2225.ClientboundPlayAudioContentPacket.from_bytes(bytes(PACKET)) == PACKET
