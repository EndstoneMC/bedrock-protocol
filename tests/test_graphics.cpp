#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("GraphicsOverrideParameterPacket: id + round-trip with a dict field")
{
    STATIC_REQUIRE(bp::GraphicsOverrideParameterPacket::Id == 331);

    bp::GraphicsOverrideParameterPacket pkt;
    pkt.parameter_keyframe_values = {{1.0f, bp::Vec3{2.0f, 3.0f, 4.0f}}};
    pkt.identifier_for_parameter = bp::GraphicsOverrideParameterType::HorizonBlendMin;
    pkt.reset_parameter = false;

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == std::vector<std::uint8_t>{
        0x01,                                            // map: uvarint32 count 1
        0x00, 0x00, 0x80, 0x3F,                          // key: float 1.0
        0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x40, 0x40,  // value: Vec3{2, 3, 4}
        0x00, 0x00, 0x80, 0x40,
        0x00,                                            // float_value: absent
        0x00,                                            // vec3_value: absent
        0x00,                                            // biome_identifier: ""
        0x02,                                            // parameter type: HorizonBlendMin
        0x00,                                            // reset_parameter: false
    });

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::GraphicsOverrideParameterPacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->parameter_keyframe_values.size() == 1);
    REQUIRE(rt->parameter_keyframe_values.at(1.0f).y == 3.0f);
    REQUIRE_FALSE(rt->float_value.has_value());
}
