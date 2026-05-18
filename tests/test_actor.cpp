#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("AnimatePacket: id + round-trip with present string-enum swing source")
{
    STATIC_REQUIRE(bp::AnimatePacket::Id == 44);

    bp::AnimatePacket pkt;
    pkt.action = bp::AnimatePacket::Action::MagicCriticalHit;
    pkt.target_runtime_id = static_cast<bp::ActorRuntimeID>(7);
    pkt.data = 1.5f;
    pkt.swing_source = bp::ActorSwingSource::Attack;  // serialized as the name "attack"

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == std::vector<std::uint8_t>{
        0x05, 0x07, 0x00, 0x00, 0xC0, 0x3F, 0x01, 0x06, 'a', 't', 't', 'a', 'c', 'k',
    });

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::AnimatePacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(rt->action == bp::AnimatePacket::Action::MagicCriticalHit);
    REQUIRE(rt->target_runtime_id == static_cast<bp::ActorRuntimeID>(7));
    REQUIRE(rt->data == 1.5f);
    REQUIRE(rt->swing_source.has_value());
    REQUIRE(*rt->swing_source == bp::ActorSwingSource::Attack);
}

TEST_CASE("AnimatePacket: round-trip with absent swing source")
{
    bp::AnimatePacket pkt;
    pkt.action = bp::AnimatePacket::Action::Swing;
    pkt.target_runtime_id = static_cast<bp::ActorRuntimeID>(1);
    pkt.data = 0.0f;

    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);
    REQUIRE(buf == std::vector<std::uint8_t>{0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00});

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::AnimatePacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE_FALSE(rt->swing_source.has_value());
}
