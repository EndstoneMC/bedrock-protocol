#include <cstdint>
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

// BiomeNoiseGradientSurfaceData sits four optionals deep inside
// BiomeDefinitionListPacket (122), which is not modelled, so the goldens exercise the
// type's own serializer rather than a packet body.

// Golden derived from gophertunnel's BiomeNoiseGradientSurface.Marshal as it stood
// before the 1.26.30 bump: FuncSlice(NonReplaceableBlocks, Uint32) and
// FuncSlice(GradientBlocks, Uint32) -- both a varuint32 count over fixed LE uint32 --
// then String(NoiseSeedString), Int32(FirstOctave) fixed LE, and
// FuncSlice(Amplitudes, Float32).
const std::string golden_v975 = bytes({
    0x01,                          // non_replaceable_blocks: count = 1 (uvarint32)
    0x07, 0x00, 0x00, 0x00,        //   [0] = 7 (uint32)
    0x01,                          // gradient_blocks: count = 1 (uvarint32)
    0x09, 0x00, 0x00, 0x00,        //   [0] = 9 (uint32)
    0x04, 0x73, 0x65, 0x65, 0x64,  // noise_seed_string = "seed"
    0xfd, 0xff, 0xff, 0xff,        // first_octave = -3 (int32)
    0x02,                          // amplitudes: count = 2 (uvarint32)
    0x00, 0x00, 0x80, 0x3f,        //   [0] = 1.0f
    0x00, 0x00, 0x00, 0x3f,        //   [1] = 0.5f
});

// The 981 reshape, gated at the 1001 snapshot. Golden from gophertunnel's current
// Marshal: the gradient blocks became NoiseBlockSpecifier elements (String, Float32,
// FloatRange, Uint32), and the three inline noise fields collapsed into a single
// NoiseDescriptor. non_replaceable_blocks is untouched.
const std::string golden_v1001 = bytes({
    0x01,                          // non_replaceable_blocks: count = 1 (uvarint32)
    0x07, 0x00, 0x00, 0x00,        //   [0] = 7 (uint32)
    0x01,                          // gradient_block_ranges: count = 1 (uvarint32)
    0x01, 0x6e,                    //   [0].noise = "n"
    0x00, 0x00, 0x80, 0x3e,        //   [0].threshold = 0.25f
    0x00, 0x00, 0x00, 0x00,        //   [0].range.min = 0.0f
    0x00, 0x00, 0x80, 0x3f,        //   [0].range.max = 1.0f
    0x09, 0x00, 0x00, 0x00,        //   [0].block_runtime_id = 9 (uint32)
    0x04, 0x73, 0x65, 0x65, 0x64,  // noise_descriptor.name = "seed"
    0xfd, 0xff, 0xff, 0xff,        // noise_descriptor.first_octave = -3 (int32)
    0x02,                          // noise_descriptor.amplitudes: count = 2 (uvarint32)
    0x00, 0x00, 0x80, 0x3f,        //   [0] = 1.0f
    0x00, 0x00, 0x00, 0x3f,        //   [1] = 0.5f
});

}  // namespace

TEST_CASE("biome noise gradient v975 form round-trips against the golden")
{
    using Data = bp::BiomeNoiseGradientSurfaceData_<bp::ProtocolVersion::V975>;

    Data data;
    data.non_replaceable_blocks = {7};
    data.gradient_blocks = {9};
    data.noise_seed_string = "seed";
    data.first_octave = -3;
    data.amplitudes = {1.0f, 0.5f};
    REQUIRE(encode(data) == golden_v975);

    bp::BinaryReader reader{golden_v975};
    auto back = bp::Serializer<Data>::deserialize(reader);
    REQUIRE(back.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    REQUIRE(back->gradient_blocks == std::vector<std::uint32_t>{9});
    REQUIRE(back->noise_seed_string == "seed");
    REQUIRE(back->first_octave == -3);
    REQUIRE(back->amplitudes.size() == 2);
}

TEST_CASE("biome noise gradient v1001 form round-trips against the golden")
{
    using Data = bp::BiomeNoiseGradientSurfaceData_<bp::ProtocolVersion::V1001>;

    Data data;
    data.non_replaceable_blocks = {7};
    data.gradient_block_ranges.push_back({.noise = "n",
                                          .threshold = 0.25f,
                                          .range = {.min = 0.0f, .max = 1.0f},
                                          .block_runtime_id = 9});
    data.noise_descriptor = {.name = "seed", .first_octave = -3, .amplitudes = {1.0f, 0.5f}};
    REQUIRE(encode(data) == golden_v1001);

    bp::BinaryReader reader{golden_v1001};
    auto back = bp::Serializer<Data>::deserialize(reader);
    REQUIRE(back.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    REQUIRE(back->gradient_block_ranges.size() == 1);
    REQUIRE(back->gradient_block_ranges[0].noise == "n");
    REQUIRE(back->gradient_block_ranges[0].range.max == 1.0f);
    REQUIRE(back->gradient_block_ranges[0].block_runtime_id == 9);
    REQUIRE(back->noise_descriptor.name == "seed");
    REQUIRE(back->noise_descriptor.first_octave == -3);
    REQUIRE(back->noise_descriptor.amplitudes.size() == 2);
}

// 981 rewrote the type around its one surviving field: a v975 body carries the same
// leading non_replaceable_blocks but diverges immediately after.
TEST_CASE("the 981 reshape changes the wire past the first field")
{
    REQUIRE(golden_v975 != golden_v1001);
    REQUIRE(golden_v975.substr(0, 5) == golden_v1001.substr(0, 5));
}
