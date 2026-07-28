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

// Golden derived from gophertunnel's ClientboundUpdateSoundData.Marshal:
// io.Uint64(ServerSoundHandle) then io.String(SoundEvent) -- a fixed LE uint64
// followed by a varuint32-length-prefixed string. One patch: the name-code is the
// PEP 8 member (STOP) where gophertunnel spells the constant "Stop". BDS lowercases
// the string before the enum lookup, so the casing is not load-bearing on the wire.
const std::string golden = bytes({
    0x2a, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // server_sound_handle = 42 (LE uint64)
    0x04, 0x53, 0x54, 0x4f, 0x50,                    // sound_event "STOP"
});

// gophertunnel / BDS spell it "Stop"; the read lowercases, so it still resolves.
const std::string golden_bds_casing = bytes({
    0x2a, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // server_sound_handle = 42 (LE uint64)
    0x04, 0x53, 0x74, 0x6f, 0x70,                    // sound_event "Stop"
});

}  // namespace

TEST_CASE("packet id is 348")
{
    STATIC_REQUIRE(bp::ClientboundUpdateSoundDataPacket_<1001>::Id == 348);
}

TEST_CASE("update-sound-data round-trips against the golden")
{
    using Packet = bp::ClientboundUpdateSoundDataPacket_<1001>;

    Packet packet;
    packet.server_sound_handle.value = 42;
    packet.sound_event = bp::SoundDataEvent::STOP;
    REQUIRE(encode(packet) == golden);

    bp::BinaryReader reader{golden};
    auto back = bp::Serializer<Packet>::deserialize(reader);
    REQUIRE(back.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    REQUIRE(back->server_sound_handle.value == 42);
    REQUIRE(back->sound_event == bp::SoundDataEvent::STOP);
}

TEST_CASE("the name-code read is case-insensitive")
{
    using Packet = bp::ClientboundUpdateSoundDataPacket_<1001>;

    bp::BinaryReader reader{golden_bds_casing};
    auto back = bp::Serializer<Packet>::deserialize(reader);
    REQUIRE(back.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    REQUIRE(back->sound_event == bp::SoundDataEvent::STOP);
}
