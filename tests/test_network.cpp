#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("RequestNetworkSettingsPacket: id + big-endian round-trip")
{
    STATIC_REQUIRE(bp::RequestNetworkSettingsPacket::id == 193);

    bp::RequestNetworkSettingsPacket pkt{975};

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == std::vector<std::uint8_t>{0x00, 0x00, 0x03, 0xCF});  // big-endian 975

    bp::ReadOnlyBinaryStream in{buf};
    auto rt = bp::deserialize<bp::RequestNetworkSettingsPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->client_network_version == 975);
}
