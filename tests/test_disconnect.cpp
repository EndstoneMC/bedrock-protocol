#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

#include "protocol/disconnect.hpp"

namespace bp = bedrock::protocol;

TEST_CASE("DisconnectFailReason enum values are stable")
{
    using DisconnectFailReason_v974 = bp::DisconnectFailReason<974>;
    REQUIRE(static_cast<int>(DisconnectFailReason_v974::Unknown) == 0);
    REQUIRE(static_cast<int>(DisconnectFailReason_v974::CantConnectNoInternet) == 1);
    REQUIRE(static_cast<int>(DisconnectFailReason_v974::NoPermissions) == 2);
    REQUIRE(static_cast<int>(DisconnectFailReason_v974::UnrecoverableError) == 3);
    REQUIRE(static_cast<int>(DisconnectFailReason_v974::ThirdPartyBlocked) == 4);

    using DisconnectFailReason_v986 = bp::DisconnectFailReason<986>;
    REQUIRE(static_cast<int>(DisconnectFailReason_v986::HostDisconnected) == 140);
}
