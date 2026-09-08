#include <string>

#include <bedrock/protocol/presence.h>

#include "fixture.hpp"

// 2208 added the packet, so there is no golden: gophertunnel and CloudburstMC both stop
// at 2168 and neither can marshal it. The shape below is the r26_u6 dump's -- a
// name-coded MatchmakingState, then the destination -- and the assertions are structural.

TEST_CASE("packet id is 353 and 2192 does not have it")
{
    STATIC_REQUIRE(bp::ClientboundMatchmakingStatePacket_<2208>::Id == 353);
    STATIC_REQUIRE(bp::has_packet_v<2208, 353>);
    STATIC_REQUIRE_FALSE(bp::has_packet_v<2192, 353>);
}

TEST_CASE("ClientboundMatchmakingStatePacket: v2208 round-trip")
{
    using Packet = bp::ClientboundMatchmakingStatePacket_<2208>;

    Packet packet;
    packet.state = bp::MatchmakingState::Matchmaking;
    packet.destination_name = "lobby";

    const auto encoded = encode(packet);
    REQUIRE(encoded == bytes({0x0b, 'm', 'a', 't', 'c', 'h', 'm', 'a', 'k', 'i', 'n', 'g',
                              0x05, 'l', 'o', 'b', 'b', 'y'}));

    const auto back = decode<Packet>(encoded);
    REQUIRE(back.state == bp::MatchmakingState::Matchmaking);
    REQUIRE(back.destination_name == "lobby");
}

// The enumerator joins where the schema's PEP 8 member separates, so the fold has to
// drop the underscore rather than keep it.
TEST_CASE("MATCH_FOUND reaches the wire as matchfound")
{
    using Packet = bp::ClientboundMatchmakingStatePacket_<2208>;

    Packet packet;
    packet.state = bp::MatchmakingState::MatchFound;
    packet.destination_name = "";

    REQUIRE(encode(packet) == bytes({0x0a, 'm', 'a', 't', 'c', 'h', 'f', 'o', 'u', 'n', 'd', 0x00}));
    REQUIRE(decode<Packet>(encode(packet)).state == bp::MatchmakingState::MatchFound);
}
