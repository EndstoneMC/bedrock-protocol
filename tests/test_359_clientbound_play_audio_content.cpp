#include <string>

#include <bedrock/protocol/sound.h>

#include "fixture.hpp"

// 2225 added the packet, so there is no golden: gophertunnel and CloudburstMC both stop
// at 2168. The shape below is the r26_u6 dump's -- two signed JWTs, a name-coded
// playback type, then a whole PlaySoundPacket body inline.

TEST_CASE("packet id is 359 and 2193 does not have it")
{
    STATIC_REQUIRE(bp::ClientboundPlayAudioContentPacket_<2225>::Id == 359);
    STATIC_REQUIRE(bp::has_packet_v<2225, 359>);
    STATIC_REQUIRE_FALSE(bp::has_packet_v<2193, 359>);
}

TEST_CASE("ClientboundPlayAudioContentPacket: the play sound body rides inline")
{
    using Packet = bp::ClientboundPlayAudioContentPacket_<2225>;

    bp::PlaySoundPacket_<2225> sound;
    sound.name = "record.cat";
    sound.pos = {.x = 1, .y = 2, .z = 3};
    sound.volume = 1.0f;
    sound.pitch = 1.0f;

    Packet packet;
    packet.shared_metadata.compact_jwt = "a.b.c";
    packet.playback_content.compact_jwt = "d.e.f";
    packet.playback_type = bp::AudioContentPlaybackType::Music;
    packet.play_sound = sound;

    const auto encoded = encode(packet);
    REQUIRE(encoded == bytes({0x05, 'a', '.', 'b', '.', 'c', 0x05, 'd', '.', 'e', '.', 'f', 0x05, 'm', 'u', 's', 'i',
                              'c'}) +
                           encode(sound));

    const auto back = decode<Packet>(encoded);
    REQUIRE(back.playback_type == bp::AudioContentPlaybackType::Music);
    REQUIRE(back.play_sound.name == "record.cat");
}

TEST_CASE("AudioContentPlaybackType reaches the wire folded")
{
    STATIC_REQUIRE(bp::enum_name(bp::AudioContentPlaybackType::Sound) == "sound");
}
