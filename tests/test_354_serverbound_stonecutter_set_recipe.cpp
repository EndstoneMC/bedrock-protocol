#include <string>

#include <bedrock/protocol/inventory.h>

#include "fixture.hpp"

// 2208 added the packet, so there is no golden: gophertunnel and CloudburstMC both stop
// at 2168. The shape below is the r26_u6 dump's -- the container the stonecutter screen
// is open on, then the index into its recipe list.

TEST_CASE("packet id is 354 and 2192 does not have it")
{
    STATIC_REQUIRE(bp::ServerboundStonecutterSetRecipePacket_<2208>::Id == 354);
    STATIC_REQUIRE(bp::has_packet_v<2208, 354>);
    STATIC_REQUIRE_FALSE(bp::has_packet_v<2192, 354>);
}

TEST_CASE("ServerboundStonecutterSetRecipePacket: v2208 round-trip")
{
    using Packet = bp::ServerboundStonecutterSetRecipePacket_<2208>;

    Packet packet;
    packet.container_id = bp::ContainerID::First;
    packet.recipe_index = 7;

    // A signed byte for the container, then the index as a zigzag varint.
    const auto encoded = encode(packet);
    REQUIRE(encoded == bytes({0x01, 0x0e}));

    const auto back = decode<Packet>(encoded);
    REQUIRE(back.container_id == bp::ContainerID::First);
    REQUIRE(back.recipe_index == 7);
}
