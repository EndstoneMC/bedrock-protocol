#include <cstdint>
#include <string>
#include <vector>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("LocatorBarPacket: id + hand-computed round-trip with one waypoint")
{
    STATIC_REQUIRE(bp::LocatorBarPacket::Id == 341);

    bp::LocatorBarPacket pkt;
    bp::LocatorBarWaypointPayload wp;
    wp.handle = bp::UUID{0, 1};
    wp.payload.update_flag = 1;
    wp.payload.texture_path = std::string{"a"};
    wp.action = bp::WaypointGroupAction::Add;
    pkt.waypoints.push_back(wp);

    // golden hand-computed; LocatorBarPacket not implemented in gophertunnel.
    // Layout: uvarint32(count=1), UUID(msb=0, lsb=1), uint32 update_flag, then
    // seven optional-flag bytes (only texture_path present, encoded as
    // bool=1, varuint32(len=1), 'a'), then action=Add as uint8.
    const std::vector<std::uint8_t> golden{
        0x01,                                            // count
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // UUID msb
        0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // UUID lsb
        0x01, 0x00, 0x00, 0x00,                          // update_flag
        0x00,                                            // is_visible absent
        0x00,                                            // world_position absent
        0x01, 0x01, 0x61,                                // texture_path "a"
        0x00,                                            // icon_size absent
        0x00,                                            // color absent
        0x00,                                            // client_position_authority absent
        0x00,                                            // actor_id absent
        0x01,                                            // action = Add
    };

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == golden);

    bp::BinaryReader in{golden};
    auto rt = bp::deserialize<bp::LocatorBarPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->waypoints.size() == 1);
    REQUIRE(rt->waypoints[0].handle.least_significant_bits == 1);
    REQUIRE(rt->waypoints[0].payload.update_flag == 1);
    REQUIRE(rt->waypoints[0].payload.texture_path.has_value());
    REQUIRE(*rt->waypoints[0].payload.texture_path == "a");
    REQUIRE_FALSE(rt->waypoints[0].payload.is_visible.has_value());
    REQUIRE(rt->waypoints[0].action == bp::WaypointGroupAction::Add);
}
