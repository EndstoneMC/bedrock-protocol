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

// Golden derived from gophertunnel's ServerBoundDiagnostics.Marshal: nine
// io.Float32 (fixed LE), then protocol.Slice over MemoryCategoryCounter,
// EntityDiagnosticTimingInfo and SystemDiagnosticTimingInfo (each a varuint32
// count then per-element Marshal). io.Uint8 is one byte, io.Uint64 fixed LE,
// io.String a varuint32-length-prefixed string.
const std::string golden_base = bytes({
    0x00, 0x00, 0x70, 0x42,                          // avg_fps = 60.0f
    0x00, 0x00, 0x80, 0x3f,                          // avg_server_sim_tick_time_ms = 1.0f
    0x00, 0x00, 0x00, 0x40,                          // avg_client_sim_tick_time_ms = 2.0f
    0x00, 0x00, 0x40, 0x40,                          // avg_begin_frame_time_ms = 3.0f
    0x00, 0x00, 0x80, 0x40,                          // avg_input_time_ms = 4.0f
    0x00, 0x00, 0xa0, 0x40,                          // avg_render_time_ms = 5.0f
    0x00, 0x00, 0xc0, 0x40,                          // avg_end_frame_time_ms = 6.0f
    0x00, 0x00, 0xe0, 0x40,                          // avg_remainder_time_percent = 7.0f
    0x00, 0x00, 0x00, 0x41,                          // avg_unaccounted_time_percent = 8.0f
    0x01,                                            // memory_category_values: count = 1
    0x02,                                            //   [0].category = ACTOR (uint8)
    0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  //   [0].current_bytes = 1024
    0x01,                                            // entity_diagnostics: count = 1
    0x06, 0x5a, 0x6f, 0x6d, 0x62, 0x69, 0x65,        //   [0].display_name = "Zombie"
    0x10, 0x6d, 0x69, 0x6e, 0x65, 0x63, 0x72, 0x61,  //   [0].entity = "minecraft:zombie"
    0x66, 0x74, 0x3a, 0x7a, 0x6f, 0x6d, 0x62, 0x69,  //
    0x65,                                            //
    0xf4, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  //   [0].time_in_ns = 500
    0x32,                                            //   [0].percent_of_total = 50
    0x01,                                            // system_diagnostics: count = 1
    0x07, 0x50, 0x68, 0x79, 0x73, 0x69, 0x63, 0x73,  //   [0].display_name = "Physics"
    0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  //   [0].system_index = 3
    0xfa, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  //   [0].time_in_ns = 250
    0x19,                                            //   [0].percent_of_total = 25
});

// The 978 addition, gated at the 1001 snapshot: a trailing protocol.Slice over
// ScopeDataSummary -- io.String label + io.String indentation + three io.Uint64.
const std::string golden_whisker = bytes({
    0x01,                                            // whisker_scopes: count = 1
    0x05, 0x46, 0x72, 0x61, 0x6d, 0x65,              //   [0].label = "Frame"
    0x02, 0x20, 0x20,                                //   [0].indentation = "  "
    0x84, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  //   [0].total_high_cost_ns = 900
    0x58, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  //   [0].total_mid_cost_ns = 600
    0x2c, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  //   [0].total_low_cost_ns = 300
});

const std::string golden = golden_base + golden_whisker;

template <class Packet>
void fill_base(Packet &packet)
{
    packet.avg_fps = 60.0f;
    packet.avg_server_sim_tick_time_ms = 1.0f;
    packet.avg_client_sim_tick_time_ms = 2.0f;
    packet.avg_begin_frame_time_ms = 3.0f;
    packet.avg_input_time_ms = 4.0f;
    packet.avg_render_time_ms = 5.0f;
    packet.avg_end_frame_time_ms = 6.0f;
    packet.avg_remainder_time_percent = 7.0f;
    packet.avg_unaccounted_time_percent = 8.0f;
    packet.memory_category_values.push_back({.category = bp::MemoryCategory::ACTOR, .current_bytes = 1024});
    packet.entity_diagnostics.push_back(
        {.display_name = "Zombie", .entity = "minecraft:zombie", .time_in_ns = 500, .percent_of_total = 50});
    packet.system_diagnostics.push_back(
        {.display_name = "Physics", .system_index = 3, .time_in_ns = 250, .percent_of_total = 25});
}

}  // namespace

TEST_CASE("packet id is 315")
{
    STATIC_REQUIRE(bp::ServerboundDiagnosticsPacket_<bp::ProtocolVersion::V975>::Id == 315);
    STATIC_REQUIRE(bp::ServerboundDiagnosticsPacket_<bp::ProtocolVersion::V1001>::Id == 315);
}

TEST_CASE("serverbound-diagnostics round-trips against the golden")
{
    using Packet = bp::ServerboundDiagnosticsPacket_<bp::ProtocolVersion::V1001>;

    Packet packet;
    fill_base(packet);
    packet.whisker_scopes.push_back({.label = "Frame",
                                     .indentation = "  ",
                                     .total_high_cost_ns = 900,
                                     .total_mid_cost_ns = 600,
                                     .total_low_cost_ns = 300});
    REQUIRE(encode(packet) == golden);

    bp::BinaryReader reader{golden};
    auto back = bp::Serializer<Packet>::deserialize(reader);
    REQUIRE(back.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    REQUIRE(back->avg_fps == 60.0f);
    REQUIRE(back->memory_category_values.size() == 1);
    REQUIRE(back->memory_category_values[0].category == bp::MemoryCategory::ACTOR);
    REQUIRE(back->memory_category_values[0].current_bytes == 1024);
    REQUIRE(back->entity_diagnostics.size() == 1);
    REQUIRE(back->entity_diagnostics[0].entity == "minecraft:zombie");
    REQUIRE(back->system_diagnostics.size() == 1);
    REQUIRE(back->system_diagnostics[0].system_index == 3);
    REQUIRE(back->whisker_scopes.size() == 1);
    REQUIRE(back->whisker_scopes[0].label == "Frame");
    REQUIRE(back->whisker_scopes[0].total_high_cost_ns == 900);
    REQUIRE(back->whisker_scopes[0].total_mid_cost_ns == 600);
    REQUIRE(back->whisker_scopes[0].total_low_cost_ns == 300);
}

TEST_CASE("before v1001 the whisker scopes are absent from the wire")
{
    using Packet = bp::ServerboundDiagnosticsPacket_<bp::ProtocolVersion::V975>;

    Packet packet;
    fill_base(packet);
    REQUIRE(encode(packet) == golden_base);

    bp::BinaryReader reader{golden_base};
    auto back = bp::Serializer<Packet>::deserialize(reader);
    REQUIRE(back.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    REQUIRE(back->system_diagnostics.size() == 1);
    REQUIRE(back->system_diagnostics[0].display_name == "Physics");
}
