#include <string>

#include <bedrock/protocol/common.h>
#include <bedrock/protocol/diagnostics.h>

#include "fixture.hpp"

namespace {

// gophertunnel's &packet.ClientBoundDebugRenderer still marshals the pre-cereal body: no
// presence flag ahead of the marker data, the marker data gated on Type == AddCube rather
// than on a flag, and the colour as four float32 RGBA channels. r26_u4 dumps
// DebugMarkerData as an optional whose colour is one int32 mce::Color, and
// ClientboundDebugRendererPacket.h declares std::optional<DebugMarkerData> holding a
// single Color. The bytes below still come out of gophertunnel's protocol.Writer, driven
// over the dump's field list (String, Bool, String, Vec3, Int32, Uint64) instead of its
// own packet struct; the regions the two shapes share are byte-identical to what
// &packet.ClientBoundDebugRenderer wrote.
// packet: Type AddDebugMarkerCube, DebugMarkerData{Text: "marker",
// Position: Vec3{1, 2, 3}, Color: 0x44556677, duration: 1500}
const std::string golden_add_cube = bytes({
    0x12, 0x61, 0x64, 0x64, 0x64, 0x65, 0x62, 0x75, 0x67, 0x6d, 0x61, 0x72,
    0x6b, 0x65, 0x72, 0x63, 0x75, 0x62, 0x65, 0x01, 0x06, 0x6d, 0x61, 0x72,
    0x6b, 0x65, 0x72, 0x00, 0x00, 0x80, 0x3f, 0x00, 0x00, 0x00, 0x40, 0x00,
    0x00, 0x40, 0x40, 0x77, 0x66, 0x55, 0x44, 0xdc, 0x05, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00,
});

// generated the same way, and patched the same way.
// packet: Type Invalid, no DebugMarkerData
const std::string golden_invalid = bytes({
    0x07, 0x69, 0x6e, 0x76, 0x61, 0x6c, 0x69, 0x64, 0x00,
});

// generated the same way, and patched the same way.
// packet: Type ClearDebugMarkers, DebugMarkerData{Text: "",
// Position: Vec3{0, 0, 0}, Color: -1, duration: 255}
const std::string golden_clear_with_marker = bytes({
    0x11, 0x63, 0x6c, 0x65, 0x61, 0x72, 0x64, 0x65, 0x62, 0x75, 0x67, 0x6d,
    0x61, 0x72, 0x6b, 0x65, 0x72, 0x73, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff,
    0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
});

}  // namespace

TEST_CASE("packet id is 164")
{
    STATIC_REQUIRE(bp::ClientboundDebugRendererPacket_<2168>::Id == 164);
    STATIC_REQUIRE_FALSE(bp::has_packet_v<1001, 164>);
    STATIC_REQUIRE(bp::has_packet_v<2168, 164>);
}

TEST_CASE("clientbound debug renderer add-cube round-trips against the golden")
{
    bp::ClientboundDebugRendererPacket_<2168> packet;
    packet.type = bp::ClientboundDebugRendererPacket_<2168>::PayloadType::ADD_DEBUG_MARKER_CUBE;
    packet.debug_marker_data = bp::ClientboundDebugRendererPacket_<2168>::DebugMarkerData{
        .text = "marker",
        .position = bp::Vec3{.x = 1.0F, .y = 2.0F, .z = 3.0F},
        .color = bp::Color{0x44556677},
        .duration_ms = 1500,
    };
    REQUIRE(encode(packet) == golden_add_cube);

    const auto back = decode<bp::ClientboundDebugRendererPacket_<2168>>(golden_add_cube);
    REQUIRE(back.type == bp::ClientboundDebugRendererPacket_<2168>::PayloadType::ADD_DEBUG_MARKER_CUBE);
    REQUIRE(back.debug_marker_data.has_value());
    REQUIRE(back.debug_marker_data->text == "marker");
    REQUIRE(back.debug_marker_data->position.x == 1.0F);
    REQUIRE(back.debug_marker_data->position.y == 2.0F);
    REQUIRE(back.debug_marker_data->position.z == 3.0F);
    REQUIRE(back.debug_marker_data->color == bp::Color{0x44556677});
    REQUIRE(back.debug_marker_data->duration_ms == 1500);
}

TEST_CASE("an absent debug marker spends a presence byte and nothing after it")
{
    bp::ClientboundDebugRendererPacket_<2168> packet;
    packet.type = bp::ClientboundDebugRendererPacket_<2168>::PayloadType::INVALID;
    REQUIRE(encode(packet) == golden_invalid);

    const auto back = decode<bp::ClientboundDebugRendererPacket_<2168>>(golden_invalid);
    REQUIRE(back.type == bp::ClientboundDebugRendererPacket_<2168>::PayloadType::INVALID);
    REQUIRE_FALSE(back.debug_marker_data.has_value());
}

TEST_CASE("the debug marker's presence is not gated on the payload type")
{
    bp::ClientboundDebugRendererPacket_<2168> packet;
    packet.type = bp::ClientboundDebugRendererPacket_<2168>::PayloadType::CLEAR_DEBUG_MARKERS;
    packet.debug_marker_data = bp::ClientboundDebugRendererPacket_<2168>::DebugMarkerData{
        .text = "",
        .position = bp::Vec3{.x = 0.0F, .y = 0.0F, .z = 0.0F},
        .color = bp::Color{-1},
        .duration_ms = 255,
    };
    REQUIRE(encode(packet) == golden_clear_with_marker);

    const auto back = decode<bp::ClientboundDebugRendererPacket_<2168>>(golden_clear_with_marker);
    REQUIRE(back.type == bp::ClientboundDebugRendererPacket_<2168>::PayloadType::CLEAR_DEBUG_MARKERS);
    REQUIRE(back.debug_marker_data.has_value());
    REQUIRE(back.debug_marker_data->text.empty());
    REQUIRE(back.debug_marker_data->color == bp::Color{-1});
    REQUIRE(back.debug_marker_data->duration_ms == 255);
}
