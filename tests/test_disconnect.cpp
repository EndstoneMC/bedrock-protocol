#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

TEST_CASE("DisconnectFailReason enum values are stable")
{
    REQUIRE(static_cast<int>(DisconnectFailReason::UNKNOWN) == 0);
    REQUIRE(static_cast<int>(DisconnectFailReason::CANT_CONNECT_NO_INTERNET) == 1);
    REQUIRE(static_cast<int>(DisconnectFailReason::NO_PERMISSIONS) == 2);
    REQUIRE(static_cast<int>(DisconnectFailReason::UNRECOVERABLE_ERROR) == 3);
    REQUIRE(static_cast<int>(DisconnectFailReason::THIRD_PARTY_BLOCK) == 4);
}
