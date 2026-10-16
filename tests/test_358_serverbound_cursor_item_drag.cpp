#include <string>

#include <bedrock/protocol/inventory.h>

#include "fixture.hpp"

// 2225 added the packet, so there is no golden: gophertunnel and CloudburstMC both stop
// at 2168. The shape below is the r26_u6 dump's -- one CursorItemDragState byte.

TEST_CASE("packet id is 358 and 2193 does not have it")
{
    STATIC_REQUIRE(bp::ServerboundCursorItemDragPacket_<2225>::Id == 358);
    STATIC_REQUIRE(bp::has_packet_v<2225, 358>);
    STATIC_REQUIRE_FALSE(bp::has_packet_v<2193, 358>);
}

TEST_CASE("ServerboundCursorItemDragPacket: v2225 round-trip")
{
    using Packet = bp::ServerboundCursorItemDragPacket_<2225>;

    Packet packet;
    packet.state = bp::CursorItemDragState::Stop;

    const auto encoded = encode(packet);
    REQUIRE(encoded == bytes({0x01}));
    REQUIRE(decode<Packet>(encoded).state == bp::CursorItemDragState::Stop);
}
