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

// Golden derived from gophertunnel's BiomeDefinitionList.Marshal (654cd5f):
// protocol.Slice writes a varuint32 count then each BiomeDefinition, whose Marshal
// leads with Int16(NameIndex) -- BDS's map key -- before the definition body, so the
// slice and BDS's std::map<unsigned short, BiomeDefinitionData> are the same bytes.
// Then Int16(BiomeID), five Float32 (fixed LE), Int32(MapWaterColour), Bool(Rain),
// OptionalFunc(Tags) and OptionalMarshaler(ChunkGeneration) -- each a bool flag then
// payload. FuncSlice(StringList, io.String) is a varuint32 count of varuint32-length
// strings, which is exactly BiomeStringList's own body.
const std::string golden = bytes({
    0x01,                                      // biome_data: count = 1 (uvarint32)
    0x00, 0x00,                                //   [0] key = 0 (uint16, string index)
    0x01, 0x00,                                //   [0].id = 1 (uint16)
    0x00, 0x00, 0x00, 0x3f,                    //   [0].temperature = 0.5f
    0x00, 0x00, 0x80, 0x3e,                    //   [0].downfall = 0.25f
    0x00, 0x00, 0x00, 0x00,                    //   [0].foliage_snow = 0.0f
    0x00, 0x00, 0x00, 0x3e,                    //   [0].depth = 0.125f
    0x00, 0x00, 0x80, 0x3f,                    //   [0].scale = 1.0f
    0x77, 0x66, 0x55, 0x44,                    //   [0].map_water_color_argb = 0x44556677
    0x01,                                      //   [0].rain = true
    0x01,                                      //   [0].tags present (bool)
    0x02,                                      //     count = 2 (uvarint32)
    0x02, 0x00,                                //     [0] = 2 (uint16)
    0x03, 0x00,                                //     [1] = 3 (uint16)
    0x00,                                      //   [0].chunk_gen_data absent (bool)
    0x02,                                      // string_list.strings: count = 2
    0x06, 0x70, 0x6c, 0x61, 0x69, 0x6e, 0x73,  //   [0] = "plains"
    0x03, 0x74, 0x61, 0x67,                    //   [1] = "tag"
});

}  // namespace

TEST_CASE("biome definition list round-trips against the golden")
{
    using Packet = bp::BiomeDefinitionListPacket;

    Packet packet;
    packet.biome_data[static_cast<bp::BiomeStringIndex>(0)] = {
        .id = 1,
        .temperature = 0.5f,
        .downfall = 0.25f,
        .foliage_snow = 0.0f,
        .depth = 0.125f,
        .scale = 1.0f,
        .map_water_color_argb = 0x44556677,
        .rain = true,
        .tags = bp::BiomeTagsData{.tags = {2, 3}},
    };
    packet.string_list.strings = {"plains", "tag"};
    REQUIRE(encode(packet) == golden);

    bp::BinaryReader reader{golden};
    auto back = bp::Serializer<Packet>::deserialize(reader);
    REQUIRE(back.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    REQUIRE(back->biome_data.size() == 1);

    const auto &definition = back->biome_data.at(static_cast<bp::BiomeStringIndex>(0));
    REQUIRE(definition.id == 1);
    REQUIRE(definition.temperature == 0.5f);
    REQUIRE(definition.map_water_color_argb == 0x44556677);
    REQUIRE(definition.rain);
    REQUIRE(definition.tags.has_value());
    REQUIRE(definition.tags->tags == std::vector<std::uint16_t>{2, 3});
    REQUIRE_FALSE(definition.chunk_gen_data.has_value());
    REQUIRE(back->string_list.strings == std::vector<std::string>{"plains", "tag"});
}

// Each key immediately precedes its own value, and std::map orders the entries by
// key regardless of insertion order.
TEST_CASE("the biome definition map writes ascending key/value pairs")
{
    bp::BiomeDefinitionListPacket packet;
    packet.biome_data[static_cast<bp::BiomeStringIndex>(5)] = {.id = 50};
    packet.biome_data[static_cast<bp::BiomeStringIndex>(2)] = {.id = 20};

    // key + id + 5 floats + colour + rain + both optionals absent.
    constexpr int entry = 2 + 2 + (5 * 4) + 4 + 1 + 1 + 1;

    const std::string wire = encode(packet);
    REQUIRE(wire.size() == 1 + (2 * entry) + 1);  // count, both entries, empty pool
    REQUIRE(wire[0] == 0x02);                     // count
    REQUIRE(wire[1] == 0x02);                     // first key = 2, not the 5 inserted first
    REQUIRE(wire[3] == 20);                       //   its own id follows immediately
    REQUIRE(wire[1 + entry] == 0x05);
    REQUIRE(wire[3 + entry] == 50);
}
