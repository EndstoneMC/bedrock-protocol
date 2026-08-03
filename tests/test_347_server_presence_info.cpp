#include <optional>
#include <string>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

namespace {

template <class T>
std::string encode(const T &value)
{
    std::string buffer;
    bp::BinaryWriter writer{buffer};
    bp::Serializer<T>::serialize(writer, value);
    return buffer;
}

std::string bytes(std::initializer_list<int> raw)
{
    std::string out;
    for (int b : raw) {
        out.push_back(static_cast<char>(b));
    }
    return out;
}

// Golden derived from gophertunnel's ServerPresenceInfo.Marshal as it stood at the
// 1.26.20 bump (e76ee66): protocol.OptionalMarshaler writes a single bool flag then
// the payload, whose Marshal was r.String(ExperienceName), r.String(WorldName) --
// each a varuint32 length + bytes.
const std::string golden_v975 = bytes({
    0x01, 0x04, 0x44, 0x65, 0x6d, 0x6f, 0x05, 0x57, 0x6f, 0x72, 0x6c, 0x64,
});

// 999 and 980 gated at the 1001 snapshot. Golden from gophertunnel's current
// PresenceInfo.Marshal (6353c49, the 1.26.30 bump): both names became
// OptionalFunc(r.String), putting a bool flag ahead of each, and
// r.String(RichPresenceID) was appended.
const std::string golden_v1001 = bytes({
    0x01, 0x01, 0x04, 0x44, 0x65, 0x6d, 0x6f, 0x01, 0x05, 0x57, 0x6f, 0x72,
    0x6c, 0x64, 0x03, 0x72, 0x70, 0x31,
});

// TODO: no golden for v2168. gophertunnel stops at 1001, and CloudburstMC's
// Bedrock_v2168 codec still dispatches ServerPresenceInfoPacket through
// ServerPresenceInfoSerializer_v975 -- it writes the two names and no rich
// presence id, so it reproduces golden_v975 verbatim at 2168. The v2168 cases
// below assert the shape structurally instead.

}  // namespace

TEST_CASE("packet id is 347 at every version")
{
    STATIC_REQUIRE(bp::ServerPresenceInfoPacket_<975>::Id == 347);
    STATIC_REQUIRE(bp::ServerPresenceInfoPacket_<1001>::Id == 347);
    STATIC_REQUIRE(bp::ServerPresenceInfoPacket_<2168>::Id == 347);
}

TEST_CASE("server-presence-info v975 form round-trips against the golden")
{
    using Packet = bp::ServerPresenceInfoPacket_<975>;

    Packet packet;
    packet.presence_configuration = bp::base::PresenceConfiguration{.experience_name = "Demo", .world_name = "World"};
    REQUIRE(encode(packet) == golden_v975);

    bp::BinaryReader reader{golden_v975};
    auto back = bp::Serializer<Packet>::deserialize(reader);
    REQUIRE(back.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    REQUIRE(back->presence_configuration.has_value());
    REQUIRE(back->presence_configuration->experience_name == "Demo");
    REQUIRE(back->presence_configuration->world_name == "World");
}

TEST_CASE("server-presence-info v1001 form round-trips against the golden")
{
    using Packet = bp::ServerPresenceInfoPacket_<1001>;

    Packet packet;
    packet.presence_configuration =
        bp::v1001::PresenceConfiguration{.experience_name = "Demo", .world_name = "World", .rich_presence_id = "rp1"};
    REQUIRE(encode(packet) == golden_v1001);

    bp::BinaryReader reader{golden_v1001};
    auto back = bp::Serializer<Packet>::deserialize(reader);
    REQUIRE(back.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    REQUIRE(back->presence_configuration.has_value());
    REQUIRE(back->presence_configuration->experience_name == "Demo");
    REQUIRE(back->presence_configuration->world_name == "World");
    REQUIRE(back->presence_configuration->rich_presence_id == "rp1");
}

TEST_CASE("server-presence-info v2168 form round-trips through its own serializer")
{
    using Packet = bp::ServerPresenceInfoPacket_<2168>;

    Packet packet;
    packet.presence_configuration = bp::v2168::PresenceConfiguration{.rich_presence_id = "rp1"};

    const auto encoded = encode(packet);
    REQUIRE(encoded.size() == 6);

    bp::BinaryReader reader{encoded};
    auto back = bp::Serializer<Packet>::deserialize(reader);
    REQUIRE(back.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    REQUIRE(back->presence_configuration.has_value());
    REQUIRE(back->presence_configuration->rich_presence_id == "rp1");
}

// The packet-level optional is version-shared: only the payload changed.
TEST_CASE("an absent presence configuration is a lone flag at every version")
{
    REQUIRE(encode(bp::ServerPresenceInfoPacket_<975>{}) == bytes({0x00}));
    REQUIRE(encode(bp::ServerPresenceInfoPacket_<1001>{}) == bytes({0x00}));
    REQUIRE(encode(bp::ServerPresenceInfoPacket_<2168>{}) == bytes({0x00}));
}

// 999's optionality is a shape the 975 form cannot express: there, a name is always
// on the wire, so "no name" and the empty string are the same bytes.
TEST_CASE("the 1001 form encodes an absent name as a bare flag")
{
    using Packet = bp::ServerPresenceInfoPacket_<1001>;

    Packet packet;
    packet.presence_configuration = bp::v1001::PresenceConfiguration{
        .experience_name = std::nullopt, .world_name = std::nullopt, .rich_presence_id = "rp1"};
    REQUIRE(encode(packet) == bytes({
    0x01, 0x00, 0x00, 0x03, 0x72, 0x70, 0x31,
}));
}

TEST_CASE("the v2168 form encodes an absent rich presence id as a bare flag")
{
    using Packet = bp::ServerPresenceInfoPacket_<2168>;

    Packet packet;
    packet.presence_configuration = bp::v2168::PresenceConfiguration{.rich_presence_id = std::nullopt};
    REQUIRE(encode(packet) == bytes({0x01, 0x00}));
}

// The added flags shift every byte after the first, so the two forms are a wire
// break rather than an additive step.
TEST_CASE("a v975 body does not decode as a v1001 one")
{
    REQUIRE(golden_v975 != golden_v1001);

    bp::BinaryReader reader{golden_v975};
    auto wrong = bp::Serializer<bp::ServerPresenceInfoPacket_<1001>>::deserialize(reader);
    REQUIRE_FALSE(wrong.has_value());
}

// 2168 dropped both names, so the 1001 body's leading name lands in the 2168
// rich presence id and the rest of the buffer is left over.
TEST_CASE("a v1001 body does not decode as a v2168 one")
{
    bp::BinaryReader reader{golden_v1001};
    auto wrong = bp::Serializer<bp::ServerPresenceInfoPacket_<2168>>::deserialize(reader);
    REQUIRE(wrong.has_value());
    REQUIRE(wrong->presence_configuration->rich_presence_id == "Demo");
    REQUIRE(reader.getUnreadLength() != 0);

    bp::ServerPresenceInfoPacket_<2168> packet;
    packet.presence_configuration = bp::v2168::PresenceConfiguration{.rich_presence_id = "rp1"};

    bp::BinaryReader back{encode(packet)};
    auto other_way = bp::Serializer<bp::ServerPresenceInfoPacket_<1001>>::deserialize(back);
    REQUIRE_FALSE(other_way.has_value());
}
