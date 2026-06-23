#include <cstdint>
#include <vector>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("MobArmorEquipmentPacket: id + round-trip with air armour (body slot since v712)")
{
    STATIC_REQUIRE(bp::MobArmorEquipmentPacket::Id == 32);

    bp::MobArmorEquipmentPacket pkt;
    pkt.runtime_id = 1;
    // All five slots left default: air NetworkItemStackDescriptors (id 0).

    const std::vector<std::uint8_t> golden{
        0x01,  // runtime_id varuint64 = 1
        0x00,  // helmet: air
        0x00,  // chestplate: air
        0x00,  // leggings: air
        0x00,  // boots: air
        0x00,  // body: air (present at the latest version)
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::MobArmorEquipmentPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->runtime_id == 1);
    REQUIRE(rt->helmet.id == 0);
    REQUIRE(rt->body.id == 0);
}
