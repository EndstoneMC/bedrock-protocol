#include <cstdint>
#include <vector>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("AddEntityPacket: id + empty-body round-trip")
{
    STATIC_REQUIRE(bp::AddEntityPacket::Id == 127);

    bp::AddEntityPacket pkt;

    // BDS allocates the id as AddEntity_DEPRECATED -- packet is no longer
    // serialized, so the body is empty.
    const std::vector<std::uint8_t> golden{};

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::AddEntityPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
}
