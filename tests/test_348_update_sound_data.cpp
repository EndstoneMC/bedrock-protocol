#include <cstdint>
#include <string>
#include <variant>

#include <protocol/sound.h>

#include "fixture.hpp"

namespace {

// Golden derived from gophertunnel's ClientboundUpdateSoundData.Marshal:
// io.Uint64(ServerSoundHandle) then io.String(SoundEvent) -- a fixed LE uint64
// followed by a varuint32-length-prefixed string. The name-code is "stop": BDS binds
// the enumerator `Stop` -- gophertunnel's spelling for the constant -- and cereal folds
// it at bind time, so the fold is what goes out.
const std::string golden = bytes({
    0x2a, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x73, 0x74, 0x6f,
    0x70,
});

// The binding's own casing, which nothing sends; the read folds the input, so it
// still resolves.
const std::string golden_binding_casing = bytes({
    0x2a, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x53, 0x74, 0x6f,
    0x70,
});

// TODO: confirm against BDS. The 2168 form has no golden: CloudburstMC's
// ClientboundUpdateSoundDataSerializer_v2168 writes the seven alternatives as seven
// independent optionals, each behind a present flag and a constant zero tag -- for
// handle=42 with only Stop set, 0x2a 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00,
// which no decoder can round-trip. The dump has one uvarint32-indexed variant. The
// assertions below are structural; only the handle (from the v1001 golden) and the
// float payloads (which match the CloudburstMC run byte for byte) come from a run.
const std::string handle_42 = golden.substr(0, 8);

}  // namespace

TEST_CASE("packet id is 348 at both versions")
{
    STATIC_REQUIRE(bp::ClientboundUpdateSoundDataPacket_<1001>::Id == 348);
    STATIC_REQUIRE(bp::ClientboundUpdateSoundDataPacket_<2168>::Id == 348);
}

TEST_CASE("update-sound-data round-trips against the golden")
{
    using Packet = bp::ClientboundUpdateSoundDataPacket_<1001>;

    Packet packet;
    packet.server_sound_handle.value = 42;
    packet.sound_event = bp::v1001::SoundDataEvent::STOP;
    REQUIRE(encode(packet) == golden);

    const auto back = decode<Packet>(golden);
    REQUIRE(back.server_sound_handle.value == 42);
    REQUIRE(back.sound_event == bp::v1001::SoundDataEvent::STOP);
}

TEST_CASE("the name-code read is case-insensitive")
{
    using Packet = bp::ClientboundUpdateSoundDataPacket_<1001>;

    REQUIRE(decode<Packet>(golden_binding_casing).sound_event == bp::v1001::SoundDataEvent::STOP);
}

TEST_CASE("a v2168 payload-less case is the handle plus its bare index")
{
    using Packet = bp::ClientboundUpdateSoundDataPacket_<2168>;

    Packet stop;
    stop.server_sound_handle.value = 42;
    stop.event = bp::v2168::Stop{};
    REQUIRE(encode(stop) == handle_42 + bytes({0x00}));

    Packet resume;
    resume.server_sound_handle.value = 42;
    resume.event = bp::v2168::Resume{};
    REQUIRE(encode(resume) == handle_42 + bytes({0x06}));

    const auto back = decode<Packet>(encode(resume));
    REQUIRE(back.server_sound_handle.value == 42);
    REQUIRE(std::holds_alternative<bp::v2168::Resume>(back.event));
}

TEST_CASE("a v2168 case with a payload writes it flat behind the index")
{
    using Packet = bp::ClientboundUpdateSoundDataPacket_<2168>;

    Packet volume;
    volume.server_sound_handle.value = 42;
    volume.event = bp::v2168::SetVolume{.volume = 0.5F};
    REQUIRE(encode(volume) == handle_42 + bytes({0x01, 0x00, 0x00, 0x00, 0x3f}));

    Packet fade;
    fade.server_sound_handle.value = 42;
    fade.event = bp::v2168::Fade{.duration = 1.5F, .target_volume = 0.25F};
    REQUIRE(encode(fade) ==
            handle_42 + bytes({0x03, 0x00, 0x00, 0xc0, 0x3f, 0x00, 0x00, 0x80, 0x3e}));

    const auto back = decode<Packet>(encode(fade));
    REQUIRE(std::get<bp::v2168::Fade>(back.event).duration == 1.5F);
    REQUIRE(std::get<bp::v2168::Fade>(back.event).target_volume == 0.25F);
}

// The name code became a variant index, so the two forms share only the handle.
TEST_CASE("a v2168 body does not decode as a v1001 one")
{
    bp::ClientboundUpdateSoundDataPacket_<2168> stop;
    stop.server_sound_handle.value = 42;
    stop.event = bp::v2168::Stop{};
    const std::string wire = encode(stop);
    REQUIRE(wire != golden);
    REQUIRE(rejects<bp::ClientboundUpdateSoundDataPacket_<1001>>(wire));
}
