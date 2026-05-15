#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("RequestNetworkSettingsPacket: id + big-endian round-trip")
{
    STATIC_REQUIRE(bp::RequestNetworkSettingsPacket::Id == 193);

    bp::RequestNetworkSettingsPacket pkt{975};

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == std::vector<std::uint8_t>{0x00, 0x00, 0x03, 0xCF});  // big-endian 975

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::RequestNetworkSettingsPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->client_network_version == 975);
}

TEST_CASE("NetworkSettingsPacket: id + round-trip with enum field")
{
    STATIC_REQUIRE(bp::NetworkSettingsPacket::Id == 143);

    bp::NetworkSettingsPacket pkt;
    pkt.compression_threshold = 256;
    pkt.compression_algorithm = bp::PacketCompressionAlgorithm::Snappy;
    pkt.client_throttle_enabled = true;
    pkt.client_throttle_threshold = 40;
    pkt.client_throttle_scalar = 0.75f;

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::NetworkSettingsPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->compression_threshold == 256);
    REQUIRE(rt->compression_algorithm == bp::PacketCompressionAlgorithm::Snappy);
    REQUIRE(rt->client_throttle_scalar == 0.75f);
}
