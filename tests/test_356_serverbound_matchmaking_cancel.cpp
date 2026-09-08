#include <string>

#include <bedrock/protocol/presence.h>

#include "fixture.hpp"

// 2208 added the packet and it carries no fields, so the body is empty at every version
// that has it. No golden: gophertunnel and CloudburstMC both stop at 2168.

TEST_CASE("packet id is 356 and 2192 does not have it")
{
    STATIC_REQUIRE(bp::ServerboundMatchmakingCancelPacket_<2208>::Id == 356);
    STATIC_REQUIRE(bp::has_packet_v<2208, 356>);
    STATIC_REQUIRE_FALSE(bp::has_packet_v<2192, 356>);
}

TEST_CASE("ServerboundMatchmakingCancelPacket: the body is empty")
{
    REQUIRE(encode(bp::ServerboundMatchmakingCancelPacket_<2208>{}).empty());
}
