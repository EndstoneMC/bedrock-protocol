#include <cstdint>
#include <string>
#include <variant>
#include <vector>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("SetActorDataPacket: id + round-trip over a heterogeneous SynchedActorData::DataList")
{
    STATIC_REQUIRE(bp::SetActorDataPacket::Id == 39);

    bp::SetActorDataPacket pkt;
    pkt.runtime_id = 1;

    // One data item per wire type tag we want to exercise. The active variant
    // alternative is the discriminator, so its index supplies the type tag.
    bp::DataItem byte_item;
    byte_item.id = 0;
    byte_item.value = std::uint8_t{1};  // tag Byte (0)

    bp::DataItem int_item;
    int_item.id = 1;
    int_item.value = std::int32_t{-5};  // tag Int (2), zigzag varint

    bp::DataItem string_item;
    string_item.id = 2;
    string_item.value = std::string{"hi"};  // tag String (4)

    bp::DataItem pos_item;
    pos_item.id = 3;
    pos_item.value = bp::BlockPos{1, 2, 3};  // tag Pos (6); BlockPos is signed varint x/y/z

    pkt.packed_items = {byte_item, int_item, string_item, pos_item};
    pkt.tick = 5;

    // Wire layout, per gophertunnel WriteEntityMetadata / EntityProperties:
    //   runtime_id        varuint64 = 1
    //   metadata          varuint32 count = 4, then each {varuint32 key, varuint32 type, value}
    //                       (0, Byte,   uint8  1)
    //                       (1, Int,    varint32 -5 -> zigzag 9)
    //                       (2, String, len 2 "hi")
    //                       (3, Pos,    signed varint x=1,y=2,z=3 -> zigzag 2,4,6)
    //   synched_properties varuint32 int-count = 0, varuint32 float-count = 0
    //   tick              varuint64 = 5
    const std::vector<std::uint8_t> golden{
        0x01,                          // runtime_id = 1
        0x04,                          // metadata count = 4
        0x00, 0x00, 0x01,              // id 0, Byte,   1
        0x01, 0x02, 0x09,              // id 1, Int,    -5
        0x02, 0x04, 0x02, 0x68, 0x69,  // id 2, String, "hi"
        0x03, 0x06, 0x02, 0x04, 0x06,  // id 3, Pos,    (1, 2, 3)
        0x00,                          // int properties = 0
        0x00,                          // float properties = 0
        0x05,                          // tick = 5
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::SetActorDataPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->runtime_id == 1);
    REQUIRE(rt->packed_items.size() == 4);
    REQUIRE(rt->packed_items[0].id == 0);
    REQUIRE(std::get<std::uint8_t>(rt->packed_items[0].value) == 1);
    REQUIRE(std::get<std::int32_t>(rt->packed_items[1].value) == -5);
    REQUIRE(std::get<std::string>(rt->packed_items[2].value) == "hi");
    const auto pos = std::get<bp::DataItemBlockPos>(rt->packed_items[3].value);
    REQUIRE(pos.x == 1);
    REQUIRE(pos.y == 2);
    REQUIRE(pos.z == 3);
    REQUIRE(rt->tick == 5);
}
