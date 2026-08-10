#include <string>

#include "fixture.hpp"

// 2181 added the packet, so there is no golden: gophertunnel and CloudburstMC both stop
// at 2168 and neither can marshal it. The shape below is the r26_u5 dump's -- a uint8
// furnace type, then the options as two varint32 enums around a bool -- and the
// assertions are structural.

TEST_CASE("packet id is 351 and 2168 does not have it")
{
    STATIC_REQUIRE(bp::SetPlayerFurnaceOptionsPacket_<2181>::Id == 351);
    STATIC_REQUIRE(bp::has_packet_v<2181, 351>);
    STATIC_REQUIRE_FALSE(bp::has_packet_v<2168, 351>);
}

TEST_CASE("SetPlayerFurnaceOptionsPacket: v2181 round-trip")
{
    using Packet = bp::SetPlayerFurnaceOptionsPacket_<2181>;

    Packet packet;
    packet.furnace_type = Packet::FurnaceType::SMOKER;
    packet.furnace_options.left_furnace_tab = bp::FurnaceLeftTabIndex::INVENTORY;
    packet.furnace_options.filtering = true;
    packet.furnace_options.layout = bp::FurnaceLayout::DEFAULT;

    // Every field is one byte at these values: the type byte, then a varint each side
    // of the flag.
    const auto encoded = encode(packet);
    REQUIRE(encoded.size() == 4);

    const auto back = decode<Packet>(encoded);
    REQUIRE(back.furnace_type == Packet::FurnaceType::SMOKER);
    REQUIRE(back.furnace_options.left_furnace_tab == bp::FurnaceLeftTabIndex::INVENTORY);
    REQUIRE(back.furnace_options.filtering);
    REQUIRE(back.furnace_options.layout == bp::FurnaceLayout::DEFAULT);
}
