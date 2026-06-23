#include <cstdint>
#include <vector>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("AddItemActorPacket: id + round-trip with an air item")
{
    STATIC_REQUIRE(bp::AddItemActorPacket::Id == 15);

    bp::AddItemActorPacket pkt;
    pkt.entity_id = 1;
    pkt.runtime_id = 2;
    // item left default: an air NetworkItemStackDescriptor (id 0 short-circuits).
    pkt.pos = {1.0f, 2.0f, 3.0f};
    pkt.velocity = {4.0f, 5.0f, 6.0f};
    pkt.from_fishing = false;

    const std::vector<std::uint8_t> golden{
        0x02,                                            // entity_id varint64 = 1
        0x02,                                            // runtime_id varuint64 = 2
        0x00,                                            // item: air (NetworkID 0)
        0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x00, 0x40,  // pos x=1, y=2,
        0x00, 0x00, 0x40, 0x40,                          //     z=3
        0x00, 0x00, 0x80, 0x40, 0x00, 0x00, 0xA0, 0x40,  // velocity x=4, y=5,
        0x00, 0x00, 0xC0, 0x40,                          //          z=6
        0x00,                                            // metadata count = 0
        0x00,                                            // from_fishing = false
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::AddItemActorPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->entity_id == 1);
    REQUIRE(rt->runtime_id == 2);
    REQUIRE(rt->item.id == 0);
    REQUIRE(rt->pos.z == 3.0f);
    REQUIRE(rt->velocity.x == 4.0f);
    REQUIRE(rt->packed_items.empty());
    REQUIRE(rt->from_fishing == false);
}
