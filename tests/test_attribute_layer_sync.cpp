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

// A case-2 (UpdateEnvironmentAttributes) packet carrying one bool attribute.
// The only version-varying part is EnvironmentAttributeData, which gains
// local_transition_ticks + noise_transition at the 976 step.
template <bp::ProtocolVersion V>
bp::ClientboundAttributeLayerSyncPacket_<V> make_packet()
{
    bp::EnvironmentAttributeData_<V> env;
    env.name = "temp";
    env.attribute = bp::BoolAttributeData{true, bp::BoolAttributeOperation::Override};
    env.current_transition_ticks = 0;
    env.total_transition_ticks = 0;
    env.easing = "linear";
    if constexpr (V == bp::ProtocolVersion::V1001) {
        env.local_transition_ticks = 0;
        env.noise_transition = false;
    }

    bp::UpdateEnvironmentAttributesData_<V> inner;
    inner.layer_name = "wet";
    inner.layer_dimension_id = static_cast<bp::DimensionType>(0);
    inner.attributes = {env};

    bp::ClientboundAttributeLayerSyncPacket_<V> packet;
    packet.data = inner;
    return packet;
}

// Golden bytes derived from CloudburstMC/Protocol's ClientboundAttributeLayerSync
// v944/v975 serializer (the authoritative per-version wire encoder), body only.
const std::string golden_v975 = bytes({
    0x02,                                              // payload type = UpdateEnvironmentAttributes
    0x03, 0x77, 0x65, 0x74,                            // layer name "wet"
    0x00,                                              // dimension = 0 (zigzag varint)
    0x01,                                              // attribute count = 1
    0x04, 0x74, 0x65, 0x6d, 0x70,                      // attribute name "temp"
    0x00,                                              // from_attribute absent
    0x00,                                              //   attribute type = 0 (bool)
    0x01,                                              //   bool value = true
    0x08, 0x4f, 0x56, 0x45, 0x52, 0x52, 0x49, 0x44, 0x45,  //   operation "OVERRIDE" (BDS uppercase verbatim)
    0x00,                                              // to_attribute absent
    0x00, 0x00, 0x00, 0x00,                            // current_transition_ticks = 0
    0x00, 0x00, 0x00, 0x00,                            // total_transition_ticks = 0
    0x06, 0x6c, 0x69, 0x6e, 0x65, 0x61, 0x72,          // easing "linear"
});

// v1001 = v975 plus the 976-step fields on the EnvironmentAttributeData.
const std::string golden_v1001 = bytes({
    0x02,
    0x03, 0x77, 0x65, 0x74,
    0x00,
    0x01,
    0x04, 0x74, 0x65, 0x6d, 0x70,
    0x00,
    0x00,
    0x01,
    0x08, 0x4f, 0x56, 0x45, 0x52, 0x52, 0x49, 0x44, 0x45,
    0x00,
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00,
    0x06, 0x6c, 0x69, 0x6e, 0x65, 0x61, 0x72,
    0x00, 0x00, 0x00, 0x00,                            // local_transition_ticks = 0 (LE uint32)
    0x00,                                              // noise_transition = false
});

}  // namespace

TEST_CASE("packet id is 345")
{
    STATIC_REQUIRE(bp::ClientboundAttributeLayerSyncPacket_<bp::ProtocolVersion::V975>::Id == 345);
    STATIC_REQUIRE(bp::ClientboundAttributeLayerSyncPacket_<bp::ProtocolVersion::V1001>::Id == 345);
}

TEST_CASE("v975 form round-trips against the golden")
{
    using Packet = bp::ClientboundAttributeLayerSyncPacket_<bp::ProtocolVersion::V975>;
    REQUIRE(encode(make_packet<bp::ProtocolVersion::V975>()) == golden_v975);

    bp::BinaryReader reader{golden_v975};
    auto back = bp::Serializer<Packet>::deserialize(reader);
    REQUIRE(back.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    REQUIRE(back->data.index() == 2);
}

TEST_CASE("v1001 form round-trips against the golden")
{
    using Packet = bp::ClientboundAttributeLayerSyncPacket_<bp::ProtocolVersion::V1001>;
    REQUIRE(encode(make_packet<bp::ProtocolVersion::V1001>()) == golden_v1001);

    bp::BinaryReader reader{golden_v1001};
    auto back = bp::Serializer<Packet>::deserialize(reader);
    REQUIRE(back.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    REQUIRE(back->data.index() == 2);
}
