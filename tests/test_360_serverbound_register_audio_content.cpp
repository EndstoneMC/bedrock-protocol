#include <string>

#include <bedrock/protocol/sound.h>

#include "fixture.hpp"

// 2225 added the packet, so there is no golden: gophertunnel and CloudburstMC both stop
// at 2168. The shape below is the r26_u6 dump's -- a list of registrations, each an id
// and three signed JWTs.

TEST_CASE("packet id is 360 and 2193 does not have it")
{
    STATIC_REQUIRE(bp::ServerboundRegisterAudioContentPacket_<2225>::Id == 360);
    STATIC_REQUIRE(bp::has_packet_v<2225, 360>);
    STATIC_REQUIRE_FALSE(bp::has_packet_v<2193, 360>);
}

TEST_CASE("ServerboundRegisterAudioContentPacket: v2225 round-trip")
{
    using Packet = bp::ServerboundRegisterAudioContentPacket_<2225>;

    Packet packet;
    packet.registrations.push_back({
        .audio_content_id = "id",
        .shared_metadata = {.compact_jwt = "s"},
        .server_content = {.compact_jwt = "v"},
        .playback_content = {.compact_jwt = "p"},
    });

    const auto encoded = encode(packet);
    REQUIRE(encoded == bytes({0x01, 0x02, 'i', 'd', 0x01, 's', 0x01, 'v', 0x01, 'p'}));

    const auto back = decode<Packet>(encoded);
    REQUIRE(back.registrations.size() == 1);
    REQUIRE(back.registrations[0].server_content.compact_jwt == "v");
}
