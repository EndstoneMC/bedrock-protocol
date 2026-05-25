#include <cstdint>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("ClientboundCloseFormPacket: id only (empty body)")
{
    STATIC_REQUIRE(bp::ClientboundCloseFormPacket::Id == 310);

    bp::ClientboundCloseFormPacket pkt;
    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf.empty());

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::ClientboundCloseFormPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
}
