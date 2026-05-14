#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("DisconnectFailReason: version-gated enumerators")
{
    REQUIRE(static_cast<int>(bp::DisconnectFailReason_<622>::Unknown) == 0);
    REQUIRE(static_cast<int>(bp::DisconnectFailReason_<622>::Kicked) == 55);
    REQUIRE(static_cast<int>(bp::DisconnectFailReason::DenyListed) == 135);
}

TEST_CASE("DisconnectPacketMessages: filtered_message added at v712")
{
    bp::DisconnectPacketMessages_<700> pre{"kicked"};
    REQUIRE(pre.message == "kicked");

    bp::DisconnectPacketMessages_<712> post{"kicked", "***"};
    REQUIRE(post.filtered_message == "***");
}

TEST_CASE("DisconnectPacket: id + round-trip without messages")
{
    STATIC_REQUIRE(bp::DisconnectPacket_<622>::id == 5);

    bp::DisconnectPacket pkt;
    pkt.reason = bp::DisconnectFailReason::Kicked;

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == std::vector<std::uint8_t>{0x6E, 0x01});  // zigzag(55), disc=1

    bp::ReadOnlyBinaryStream in{buf};
    auto rt = bp::deserialize<bp::DisconnectPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->reason == bp::DisconnectFailReason::Kicked);
    REQUIRE_FALSE(rt->messages.has_value());
}

TEST_CASE("DisconnectPacket: round-trip with messages")
{
    bp::DisconnectPacket pkt;
    pkt.reason = bp::DisconnectFailReason::Kicked;
    pkt.messages = bp::DisconnectPacketMessages{"bye", "***"};

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == std::vector<std::uint8_t>{
        0x6E, 0x00, 0x03, 'b', 'y', 'e', 0x03, '*', '*', '*',
    });

    bp::ReadOnlyBinaryStream in{buf};
    auto rt = bp::deserialize<bp::DisconnectPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->messages->message == "bye");
    REQUIRE(rt->messages->filtered_message == "***");
}
