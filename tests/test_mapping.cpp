#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

// Hand-computed goldens: TestMappingPacket is a synthetic Batch 0 fixture
// for `dict[K, V]` (MappingType) codegen coverage. There is no gophertunnel
// equivalent because no real BDS packet currently uses a map-typed field --
// `BiomeDefinitionListPacket` (Batch C) will be the first.

TEST_CASE("TestMappingPacket: empty map writes the length prefix only")
{
    STATIC_REQUIRE(bp::TestMappingPacket::Id == 9999);

    bp::TestMappingPacket pkt;

    const std::vector<std::uint8_t> golden{0x00};

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::TestMappingPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->entries.empty());
}

TEST_CASE("TestMappingPacket: entries serialize in std::map (key-sorted) order")
{
    bp::TestMappingPacket pkt;
    pkt.entries.emplace(7, bp::TestMappingValue{"seven", 70});
    pkt.entries.emplace(1, bp::TestMappingValue{"one", 10});
    pkt.entries.emplace(42, bp::TestMappingValue{"forty-two", 420});

    // std::map iterates by key, so the wire order is 1, 7, 42 regardless of
    // insertion order. Each entry is uint16 little-endian key, then varuint32
    // string length + bytes, then uint16 little-endian weight.
    const std::vector<std::uint8_t> golden{
        0x03,
        // key=1, "one", weight=10
        0x01, 0x00,
        0x03, 'o', 'n', 'e',
        0x0A, 0x00,
        // key=7, "seven", weight=70
        0x07, 0x00,
        0x05, 's', 'e', 'v', 'e', 'n',
        0x46, 0x00,
        // key=42, "forty-two", weight=420
        0x2A, 0x00,
        0x09, 'f', 'o', 'r', 't', 'y', '-', 't', 'w', 'o',
        0xA4, 0x01,
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::TestMappingPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->entries.size() == 3);
    REQUIRE(rt->entries.at(1).label == "one");
    REQUIRE(rt->entries.at(7).weight == 70);
    REQUIRE(rt->entries.at(42).label == "forty-two");
}
