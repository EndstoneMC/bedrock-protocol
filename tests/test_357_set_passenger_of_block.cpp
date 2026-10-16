#include <string>

#include <bedrock/protocol/actor.h>

#include "fixture.hpp"

// 2225 added the packet, so there is no golden: gophertunnel and CloudburstMC both stop
// at 2168. The shape below is the r26_u6 dump's -- the passenger, then the block it rides,
// absent when it dismounts.

TEST_CASE("packet id is 357 and 2193 does not have it")
{
    STATIC_REQUIRE(bp::SetPassengerOfBlockPacket_<2225>::Id == 357);
    STATIC_REQUIRE(bp::has_packet_v<2225, 357>);
    STATIC_REQUIRE_FALSE(bp::has_packet_v<2193, 357>);
}

TEST_CASE("SetPassengerOfBlockPacket: v2225 round-trip")
{
    using Packet = bp::SetPassengerOfBlockPacket_<2225>;

    Packet packet;
    packet.passenger = bp::ActorUniqueID{5};
    REQUIRE(encode(packet) == bytes({0x0a, 0x00}));

    packet.passenger_of_block_data = bp::PassengerOfBlockArguments{
        .block_pos = {.x = -1, .y = 64, .z = 2},
        .offset = {.x = 0.5f, .y = 0.25f, .z = 0.5f},
        .rotation = 180.0f,
        .rotation_limit = 30.0f,
        .emote_type = bp::PassengerOfBlockArguments::EmoteType::Standing,
    };
    const auto encoded = encode(packet);
    REQUIRE(encoded.size() == 2 + 1 + 2 + 1 + 12 + 4 + 4 + 1);

    const auto back = decode<Packet>(encoded);
    REQUIRE(back.passenger == bp::ActorUniqueID{5});
    REQUIRE(back.passenger_of_block_data->block_pos.x == -1);
    REQUIRE(back.passenger_of_block_data->block_pos.y == 64);
    REQUIRE(back.passenger_of_block_data->rotation == 180.0f);
    REQUIRE(back.passenger_of_block_data->emote_type == bp::PassengerOfBlockArguments::EmoteType::Standing);
}
