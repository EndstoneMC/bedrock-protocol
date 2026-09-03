#include <cstdint>
#include <string>

#include <bedrock/protocol/attribute.h>
#include <bedrock/protocol/chunk.h>

#include "fixture.hpp"

namespace {

// Golden derived from gophertunnel's SubChunkRequest.Marshal as it stood before
// the 1.26.30 bump (f53c54a7): io.Varint32(Dimension), io.SubChunkPos(Position) --
// three Varint32 -- then protocol.SliceUint32Length(Offsets), whose count is a
// fixed LE uint32. Each SubChunkOffset is three io.Int8.
const std::string golden_v975 = bytes({
    0x00, 0x02, 0x04, 0x06, 0x01, 0x00, 0x00, 0x00, 0xff, 0x00, 0x01,
});

// The 979 cerealisation, gated at the 1001 snapshot. Golden from gophertunnel's
// current SubChunkRequest.Marshal: io.Varint32(Dimension), protocol.Slice(Offsets)
// -- now a varuint32 count -- then three io.Int32 for Position, fixed LE. So the
// migration both reordered the packet and reshaped two of its three fields.
const std::string golden_v1001 = bytes({
    0x00, 0x01, 0xff, 0x00, 0x01, 0x01, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00,
    0x00, 0x03, 0x00, 0x00, 0x00,
});

}  // namespace

TEST_CASE("packet id is 175 at both versions")
{
    STATIC_REQUIRE(bp::SubChunkRequestPacket_<975>::Id == 175);
    STATIC_REQUIRE(bp::SubChunkRequestPacket_<1001>::Id == 175);
}

TEST_CASE("sub-chunk-request v975 form round-trips against the golden")
{
    using Packet = bp::SubChunkRequestPacket_<975>;

    Packet packet;
    packet.dimension_type = bp::DimensionType{0};
    packet.center_pos = {.x = 1, .y = 2, .z = 3};
    packet.sub_chunk_pos_offsets.push_back({.x = -1, .y = 0, .z = 1});
    REQUIRE(encode(packet) == golden_v975);

    const auto back = decode<Packet>(golden_v975);
    REQUIRE(back.center_pos.x == 1);
    REQUIRE(back.center_pos.z == 3);
    REQUIRE(back.sub_chunk_pos_offsets.size() == 1);
    REQUIRE(back.sub_chunk_pos_offsets[0].x == -1);
}

TEST_CASE("sub-chunk-request v1001 form round-trips against the golden")
{
    using Packet = bp::SubChunkRequestPacket_<1001>;

    Packet packet;
    packet.dimension_type = bp::DimensionType{0};
    packet.sub_chunk_pos_offsets.push_back({.x = -1, .y = 0, .z = 1});
    packet.center_pos = {.x = 1, .y = 2, .z = 3};
    REQUIRE(encode(packet) == golden_v1001);

    const auto back = decode<Packet>(golden_v1001);
    REQUIRE(back.center_pos.x == 1);
    REQUIRE(back.center_pos.z == 3);
    REQUIRE(back.sub_chunk_pos_offsets.size() == 1);
    REQUIRE(back.sub_chunk_pos_offsets[0].x == -1);
}

// The reorder and the prefix swap are what make 979 a wire break rather than an
// additive step: the same values encode to different bytes, and to different
// lengths, at the two versions.
TEST_CASE("the cerealisation reshapes the wire, not just the field order")
{
    REQUIRE(golden_v975 != golden_v1001);
    REQUIRE(golden_v975.size() == 11);
    REQUIRE(golden_v1001.size() == 17);

    // A v975 body must not decode as a v1001 one: the fixed uint32 offset count
    // reads as a varint, so the frame desynchronises rather than reading short.
    REQUIRE(rejects<bp::SubChunkRequestPacket_<1001>>(golden_v975));
}
