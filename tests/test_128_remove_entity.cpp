#include <cstdint>
#include <vector>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("RemoveEntityPacket: id + empty-body round-trip")
{
    STATIC_REQUIRE(bp::RemoveEntityPacket::Id == 128);

    bp::RemoveEntityPacket pkt;

    // BDS allocates the id as RemoveEntity_DEPRECATED -- packet is no longer
    // serialized, so the body is empty.
    const std::vector<std::uint8_t> golden{};

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::RemoveEntityPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
}
