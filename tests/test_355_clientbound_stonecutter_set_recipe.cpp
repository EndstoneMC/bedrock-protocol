#include <string>

#include <bedrock/protocol/inventory.h>

#include "fixture.hpp"

// 2208 added the packet, so there is no golden: gophertunnel and CloudburstMC both stop
// at 2168. It is the serverbound shape led by the player the selection belongs to.

TEST_CASE("packet id is 355 and 2192 does not have it")
{
    STATIC_REQUIRE(bp::ClientboundStonecutterSetRecipePacket_<2208>::Id == 355);
    STATIC_REQUIRE(bp::has_packet_v<2208, 355>);
    STATIC_REQUIRE_FALSE(bp::has_packet_v<2192, 355>);
}

TEST_CASE("ClientboundStonecutterSetRecipePacket: v2208 round-trip")
{
    using Packet = bp::ClientboundStonecutterSetRecipePacket_<2208>;

    Packet packet;
    packet.player_id = bp::ActorUniqueID{5};
    packet.container_id = bp::ContainerID::First;
    packet.recipe_index = 7;

    // A zigzag varint for the player, a signed byte for the container, then the index.
    const auto encoded = encode(packet);
    REQUIRE(encoded == bytes({0x0a, 0x01, 0x0e}));

    const auto back = decode<Packet>(encoded);
    REQUIRE(back.player_id == bp::ActorUniqueID{5});
    REQUIRE(back.container_id == bp::ContainerID::First);
    REQUIRE(back.recipe_index == 7);
}
