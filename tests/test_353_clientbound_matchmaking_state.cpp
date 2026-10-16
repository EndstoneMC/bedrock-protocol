#include <string>

#include <bedrock/protocol/presence.h>

#include "fixture.hpp"

// 2225 added the packet, so there is no golden: gophertunnel and CloudburstMC both stop
// at 2168 and neither can marshal it. The shape below is the r26_u6 dump's -- a one-byte
// MatchmakingState, the destination, then optional options -- and the assertions are
// structural.

TEST_CASE("packet id is 353 and 2193 does not have it")
{
    STATIC_REQUIRE(bp::ClientboundMatchmakingStatePacket_<2225>::Id == 353);
    STATIC_REQUIRE(bp::has_packet_v<2225, 353>);
    STATIC_REQUIRE_FALSE(bp::has_packet_v<2193, 353>);
}

TEST_CASE("ClientboundMatchmakingStatePacket: v2225 round-trip")
{
    using Packet = bp::ClientboundMatchmakingStatePacket_<2225>;

    Packet packet;
    packet.state = bp::MatchmakingState::Matchmaking;
    packet.destination_name = "lobby";

    const auto encoded = encode(packet);
    REQUIRE(encoded == bytes({0x01, 0x05, 'l', 'o', 'b', 'b', 'y', 0x00}));

    const auto back = decode<Packet>(encoded);
    REQUIRE(back.state == bp::MatchmakingState::Matchmaking);
    REQUIRE(back.destination_name == "lobby");
    REQUIRE_FALSE(back.options.has_value());
}

TEST_CASE("ClientboundMatchmakingStatePacket: the options carry two optionals of their own")
{
    using Packet = bp::ClientboundMatchmakingStatePacket_<2225>;

    Packet packet;
    packet.state = bp::MatchmakingState::PlayerLeftParty;
    packet.destination_name = "";
    packet.options = bp::MatchmakingStateOptions{.triggering_player_name = "Alex", .triggered_by_local_player = {}};

    const auto encoded = encode(packet);
    REQUIRE(encoded == bytes({0x04, 0x00, 0x01, 0x01, 0x04, 'A', 'l', 'e', 'x', 0x00}));

    const auto back = decode<Packet>(encoded);
    REQUIRE(back.state == bp::MatchmakingState::PlayerLeftParty);
    REQUIRE(back.options->triggering_player_name == "Alex");
    REQUIRE_FALSE(back.options->triggered_by_local_player.has_value());
}
