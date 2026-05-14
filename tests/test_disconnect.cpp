#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("DisconnectFailReason enum values are stable")
{
    using DisconnectFailReason_v622 = bp::DisconnectFailReason<>;
    REQUIRE(static_cast<int>(DisconnectFailReason_v622::Unknown) == 0);
    REQUIRE(static_cast<int>(DisconnectFailReason_v622::CantConnectNoInternet) == 1);
    REQUIRE(static_cast<int>(DisconnectFailReason_v622::NoPermissions) == 2);
    REQUIRE(static_cast<int>(DisconnectFailReason_v622::UnrecoverableError) == 3);
    REQUIRE(static_cast<int>(DisconnectFailReason_v622::ThirdPartyBlocked) == 4);

    using DisconnectFailReason_v986 = bp::DisconnectFailReason<986>;
    REQUIRE(static_cast<int>(DisconnectFailReason_v986::HostDisconnected) == 140);
}

TEST_CASE("DisconnectPacketMessages gains filtered_message at v712")
{
    bp::DisconnectPacketMessages<700> pre;
    pre.message = "kicked";
    REQUIRE(pre.message == "kicked");

    bp::DisconnectPacketMessages<712> post;
    post.message = "kicked";
    post.filtered_message = "***";
    REQUIRE(post.message == "kicked");
    REQUIRE(post.filtered_message == "***");
}

TEST_CASE("DisconnectPacket id is a static constexpr and reason appears at v622")
{
    STATIC_REQUIRE(bp::DisconnectPacket<622>::id == 5);

    bp::DisconnectPacket<500> old_pkt;
    old_pkt.messages = bp::DisconnectPacketMessages<500>{"bye"};
    REQUIRE(std::get<bp::DisconnectPacketMessages<500>>(old_pkt.messages).message
            == "bye");

    bp::DisconnectPacket<622> pkt;
    pkt.reason = bp::DisconnectFailReason<622>::Kicked;
    pkt.messages = std::monostate{};
    REQUIRE(pkt.reason == bp::DisconnectFailReason<622>::Kicked);
    REQUIRE(std::holds_alternative<std::monostate>(pkt.messages));
}
