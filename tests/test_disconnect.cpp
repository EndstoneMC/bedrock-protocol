#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("DisconnectFailReason enum values are stable")
{
    using DisconnectFailReason_v622 = bp::DisconnectFailReason_<622>;
    REQUIRE(static_cast<int>(DisconnectFailReason_v622::Unknown) == 0);
    REQUIRE(static_cast<int>(DisconnectFailReason_v622::CantConnectNoInternet) == 1);
    REQUIRE(static_cast<int>(DisconnectFailReason_v622::NoPermissions) == 2);
    REQUIRE(static_cast<int>(DisconnectFailReason_v622::UnrecoverableError) == 3);
    REQUIRE(static_cast<int>(DisconnectFailReason_v622::ThirdPartyBlocked) == 4);

    // Bare name resolves to DisconnectFailReason_<974>, which is v893's concrete enum.
    REQUIRE(static_cast<int>(bp::DisconnectFailReason::DenyListed) == 135);
    REQUIRE(static_cast<int>(bp::DisconnectFailReason_<974>::DenyListed) == 135);
}

TEST_CASE("DisconnectPacketMessages gains filtered_message at v712")
{
    bp::DisconnectPacketMessages_<700> pre;
    pre.message = "kicked";
    REQUIRE(pre.message == "kicked");

    bp::DisconnectPacketMessages_<712> post;
    post.message = "kicked";
    post.filtered_message = "***";
    REQUIRE(post.message == "kicked");
    REQUIRE(post.filtered_message == "***");
}

TEST_CASE("DisconnectPacket id is a static constexpr and reason appears at v622")
{
    STATIC_REQUIRE(bp::DisconnectPacket_<622>::id == 5);

    bp::DisconnectPacket_<500> old_pkt;
    old_pkt.messages = bp::DisconnectPacketMessages_<500>{"bye"};
    REQUIRE(old_pkt.messages->message == "bye");

    bp::DisconnectPacket_<622> pkt;
    pkt.reason = bp::DisconnectFailReason_<622>::Kicked;
    pkt.messages.reset();
    REQUIRE(pkt.reason == bp::DisconnectFailReason_<622>::Kicked);
    REQUIRE_FALSE(pkt.messages.has_value());
}

TEST_CASE("Serializer<DisconnectFailReason>: wire matches gophertunnel Varint32")
{
    // Gophertunnel (sandertv/gophertunnel) encodes the `reason` field with
    // `protocol.IO.Varint32`, which is zigzag-encoded signed varint:
    //   ux := uint32(x) << 1
    //   if x < 0 { ux = ^ux }
    //   WriteVaruint32(ux)
    // The expected bytes below are what gophertunnel produces for the same
    // enum value; this test serves as a wire-compat anchor against that
    // reference implementation.

    using Reason = bp::DisconnectFailReason;

    struct Case {
        Reason value;
        int raw;
        std::vector<std::uint8_t> expected;
    };
    const std::vector<Case> cases = {
        {Reason::Unknown, 0, {0x00}},                // zigzag(0)   = 0
        {Reason::CantConnectNoInternet, 1, {0x02}},  // zigzag(1)   = 2
        {Reason::Kicked, 55, {0x6E}},                // zigzag(55)  = 110
        {Reason::BadPacket, 90, {0xB4, 0x01}},       // zigzag(90)  = 180 → 0xB4 0x01
    };

    for (const auto &c : cases) {
        std::vector<std::uint8_t> buf;
        bp::BinaryStream out{buf};
        bp::serialize<Reason>(out, c.value);
        INFO("value=" << c.raw);
        REQUIRE(buf == c.expected);

        bp::ReadOnlyBinaryStream in{buf};
        auto v = bp::deserialize<Reason>(in);
        REQUIRE(v.has_value());
        REQUIRE(*v == c.value);
    }
}

TEST_CASE("Serializer<DisconnectPacket> (latest=v974): wire matches gophertunnel Marshal")
{
    SECTION("messages skipped — discriminator only")
    {
        bp::DisconnectPacket pkt;
        pkt.reason = bp::DisconnectFailReason::Kicked;  // 55
        pkt.messages.reset();

        std::vector<std::uint8_t> buf;
        bp::BinaryStream out{buf};
        bp::serialize(out, pkt);

        // [zigzag(55), discriminator=1]
        const std::vector<std::uint8_t> expected = {0x6E, 0x01};
        REQUIRE(buf == expected);

        bp::ReadOnlyBinaryStream in{buf};
        auto v = bp::deserialize<bp::DisconnectPacket>(in);
        REQUIRE(v.has_value());
        REQUIRE(v->reason == bp::DisconnectFailReason::Kicked);
        REQUIRE_FALSE(v->messages.has_value());
    }

    SECTION("messages present with both strings")
    {
        bp::DisconnectPacket pkt;
        pkt.reason = bp::DisconnectFailReason::Kicked;
        pkt.messages = bp::DisconnectPacketMessages{"bye", "***"};

        std::vector<std::uint8_t> buf;
        bp::BinaryStream out{buf};
        bp::serialize(out, pkt);

        // [zigzag(55), discriminator=0,
        //  string len=3, "bye", string len=3, "***"]
        const std::vector<std::uint8_t> expected = {
            0x6E, 0x00, 0x03, 'b', 'y', 'e', 0x03, '*', '*', '*',
        };
        REQUIRE(buf == expected);

        bp::ReadOnlyBinaryStream in{buf};
        auto v = bp::deserialize<bp::DisconnectPacket>(in);
        REQUIRE(v.has_value());
        REQUIRE(v->reason == bp::DisconnectFailReason::Kicked);
        REQUIRE(v->messages.has_value());
        REQUIRE(v->messages->message == "bye");
        REQUIRE(v->messages->filtered_message == "***");
    }
}
