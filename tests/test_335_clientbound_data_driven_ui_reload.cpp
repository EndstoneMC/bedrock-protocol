#include <cstdint>
#include <vector>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("ClientboundDataDrivenUIReloadPacket: id only (empty body)")
{
    STATIC_REQUIRE(bp::ClientboundDataDrivenUIReloadPacket::Id == 335);

    bp::ClientboundDataDrivenUIReloadPacket pkt;
    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf.empty());

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::ClientboundDataDrivenUIReloadPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
}
