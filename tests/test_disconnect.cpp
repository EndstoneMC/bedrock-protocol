#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("DisconnectFailReason enum values are stable")
{
    using bp::DisconnectFailReason;
    REQUIRE(static_cast<int>(DisconnectFailReason::Unknown) == 0);
    REQUIRE(static_cast<int>(DisconnectFailReason::CantConnectNoInternet) == 1);
    REQUIRE(static_cast<int>(DisconnectFailReason::NoPermissions) == 2);
    REQUIRE(static_cast<int>(DisconnectFailReason::UnrecoverableError) == 3);
    REQUIRE(static_cast<int>(DisconnectFailReason::ThirdPartyBlock) == 4);
}
