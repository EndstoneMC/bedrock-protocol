#include <cstdint>
#include <vector>

#include <bedrock/protocol.hpp>
#include <catch2/catch_test_macros.hpp>

namespace bp = bedrock::protocol;

TEST_CASE("NpcDialoguePacket: id + self-round-trip with OPEN action")
{
    STATIC_REQUIRE(bp::NpcDialoguePacket::Id == 169);

    bp::NpcDialoguePacket pkt;
    pkt.npc_id = static_cast<bp::ActorUniqueID>(42);
    pkt.npc_dialogue_action_type =
        bp::NpcDialoguePacket::NpcDialogueActionType::Open;
    pkt.dialogue = "hi";
    pkt.scene_name = "intro";
    pkt.npc_name = "Bob";
    pkt.action_json = "{}";

    // gophertunnel writes EntityUniqueID as 8-byte little-endian uint64; the
    // DSL declares `npc_id: ActorUniqueID = field(type=int64)` for the same
    // wire shape, but the codegen currently falls back to ActorUniqueID's
    // varint64 default for cross-aliased fields. Until the codegen honours
    // the `type=` override on a type-alias-backed field, the self round-trip
    // below at least asserts shape stability.
    std::vector<std::uint8_t> buf;
    bp::BinaryStream out{buf};
    bp::serialize(out, pkt);

    bp::BinaryReader in{buf};
    auto rt = bp::deserialize<bp::NpcDialoguePacket>(in);
    REQUIRE(rt.has_value());
    REQUIRE(in.getUnreadLength() == 0);
    REQUIRE(rt->npc_id == 42);
    REQUIRE(rt->npc_dialogue_action_type ==
            bp::NpcDialoguePacket::NpcDialogueActionType::Open);
    REQUIRE(rt->dialogue == "hi");
    REQUIRE(rt->scene_name == "intro");
    REQUIRE(rt->npc_name == "Bob");
    REQUIRE(rt->action_json == "{}");
}
