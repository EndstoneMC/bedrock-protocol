#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("LoginPacket: id + big-endian version with connection request blob")
{
    STATIC_REQUIRE(bp::LoginPacket::Id == 1);

    bp::LoginPacket pkt{975, "hello"};  // aggregate init of the generated struct

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == std::vector<std::uint8_t>{
        0x00, 0x00, 0x03, 0xCF,         // big-endian client network version 975
        0x05, 'h', 'e', 'l', 'l', 'o',  // varuint32 length + connection request bytes
    });

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::LoginPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->client_network_version == 975);
    REQUIRE(rt->connection_request == "hello");
}
