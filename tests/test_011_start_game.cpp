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

// StartGamePacket is not cerealised at 975 or 1001, so protocol-docs does not
// describe it there at all -- r26_u3 (network version 1001) has no
// StartGamePacket.json, and r26_u4 documents network version 2168, a different
// shape after the migration. The wire therefore comes from gophertunnel's
// StartGame.Marshal, cross-checked against CloudburstMC's StartGameSerializer.
//
// Everything below is one flat run of fields: cereal-style grouping (LevelSettings)
// writes its members inline, so the struct boundary costs no bytes.
const std::string golden_v975 = bytes({
    0x02,  // entity_id = 1 (varint64)
    0x02,  // runtime_id = 2 (uvarint64)
    0x00,  // entity_game_type = SURVIVAL(0) (varint32)
    0x00, 0x00, 0x80, 0x3f, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x40, 0x40,  // pos = (1,2,3) float LE
    0x00, 0x00, 0x80, 0x40, 0x00, 0x00, 0xa0, 0x40,  // rot = (4,5) float LE
    0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  //   seed = 7 (int64 LE)
    0x00, 0x00,  //   spawn.type = DEFAULT(0) (int16)
    0x00,  //   spawn.user_defined_biome_name = ""
    0x00,  //   spawn.dimension = 0 (varint32)
    0x02,  //   generator = OVERWORLD(1) (varint32)
    0x00,  //   game_type = SURVIVAL(0) (varint32)
    0x00,  //   is_hardcore = false
    0x04,  //   game_difficulty = NORMAL(2) (varint32)
    0x00, 0x80, 0x01, 0x00,  //   default_spawn = (0,64,0) varint32
    0x01,  //   achievements_disabled = true
    0x00,  //   editor_world_type = NON_EDITOR(0) (varint32)
    0x00,  //   is_created_in_editor = false
    0x00,  //   is_exported_from_editor = false
    0x00,  //   time = 0 (varint32)
    0x00,  //   education_edition_offer = NONE(0) (varint32)
    0x00,  //   education_features_enabled = false
    0x00,  //   education_product_id = ""
    0x00, 0x00, 0x00, 0x00,  //   rain_level = 0.0f
    0x00, 0x00, 0x00, 0x00,  //   lightning_level = 0.0f
    0x00,  //   confirmed_platform_locked_content = false
    0x01,  //   multiplayer_game_intent = true
    0x01,  //   lan_broadcast_intent = true
    0x04,  //   xbl_broadcast_intent = FRIENDS_ONLY(2) (varint32)
    0x04,  //   platform_broadcast_intent = FRIENDS_ONLY(2) (varint32)
    0x01,  //   commands_enabled = true
    0x00,  //   texture_packs_required = false
    0x01,  //   game_rules: count = 1 (uvarint32)
    0x0f, 0x64, 0x6f, 0x64, 0x61, 0x79, 0x6c, 0x69, 0x67, 0x68, 0x74, 0x63, 0x79, 0x63, 0x6c, 0x65,  //     [0].name = "dodaylightcycle"
    0x00,  //     [0].can_be_modified_by_player = false
    0x01,  //     [0].value: discriminator = 1 (BOOL)
    0x01,  //     [0].value = true (bool)
    0x00, 0x00, 0x00, 0x00,  //   experiments: count = 0 (fixed uint32)
    0x00,  //   experiments_previously_toggled = false
    0x00,  //   bonus_chest_enabled = false
    0x00,  //   start_with_map_enabled = false
    0x02,  //   default_permissions = MEMBER(1) (varint32)
    0x04, 0x00, 0x00, 0x00,  //   server_chunk_tick_range = 4 (int32 LE)
    0x00,  //   has_locked_behavior_pack = false
    0x00,  //   has_locked_resource_pack = false
    0x00,  //   is_from_locked_template = false
    0x00,  //   use_msa_gamertags_only = false
    0x00,  //   is_from_world_template = false
    0x00,  //   is_world_template_option_locked = false
    0x00,  //   spawn_v1_villagers = false
    0x00,  //   persona_disabled = false
    0x00,  //   custom_skins_disabled = false
    0x00,  //   emote_chat_muted = false
    0x06, 0x31, 0x2e, 0x32, 0x31, 0x2e, 0x30,  //   base_game_version = "1.21.0"
    0x00, 0x00, 0x00, 0x00,  //   limited_world_width = 0 (int32 LE)
    0x00, 0x00, 0x00, 0x00,  //   limited_world_depth = 0 (int32 LE)
    0x00,  //   nether_type = NORMAL(0) (bool)
    0x00,  //   edu_shared_uri_resource.button_name = ""
    0x00,  //   edu_shared_uri_resource.link_uri = ""
    0x00,  //   override_force_experimental_gameplay: absent
    0x00,  //   chat_restriction_level = NONE(0) (uint8)
    0x00,  //   disable_player_interactions = false
    0x03, 0x6c, 0x76, 0x6c,  // level_id = "lvl"
    0x05, 0x77, 0x6f, 0x72, 0x6c, 0x64,  // level_name = "world"
    0x00,  // template_content_identity = ""
    0x00,  // is_trial = false
    0x50,  // movement_settings.rewind_history_size = 40 (varint32)
    0x00,  // movement_settings.server_authoritative_block_breaking = false
    0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // level_current_time = 100 (int64 LE)
    0x00,  // enchantment_seed = 0 (varint32)
    0x00,  // block_properties: count = 0 (uvarint32)
    0x00,  // multiplayer_correlation_id = ""
    0x01,  // enable_item_stack_net_manager = true
    0x06, 0x31, 0x2e, 0x32, 0x31, 0x2e, 0x30,  // server_version = "1.21.0"
    0x0a, 0x00, 0x00,  // player_property_data = empty CompoundTag (named root: type, empty name, end)
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // server_block_type_registry_checksum = 0 (uint64 LE)
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  // world_template_id = {0,0} (two uint64 LE)
    0x00,  // server_enabled_client_side_generation = false
    0x01,  // block_network_ids_are_hashes = true
    0x00,  // network_permissions.server_auth_sound_enabled = false
    0x00,  // server_configuration_join_info: absent
    0x00,  // server_telemetry_data.server_id = ""
    0x00,  // server_telemetry_data.scenario_id = ""
    0x00,  // server_telemetry_data.world_id = ""
    0x00,  // server_telemetry_data.owner_id = ""
});

}  // namespace

TEST_CASE("packet id is 11 at both versions")
{
    STATIC_REQUIRE(bp::StartGamePacket_<bp::ProtocolVersion::V975>::Id == 11);
    STATIC_REQUIRE(bp::StartGamePacket_<bp::ProtocolVersion::V1001>::Id == 11);
}

template <class Packet>
static void fill(Packet &packet)
{
    packet.entity_id = static_cast<bp::ActorUniqueID>(1);
    packet.runtime_id = static_cast<bp::ActorRuntimeID>(2);
    packet.entity_game_type = bp::GameType::SURVIVAL;
    packet.pos = {.x = 1.0f, .y = 2.0f, .z = 3.0f};
    packet.rot = {.x = 4.0f, .y = 5.0f};

    auto &s = packet.settings;
    s.seed = 7;
    s.spawn_settings = {.type = bp::SpawnBiomeType::DEFAULT,
                        .user_defined_biome_name = "",
                        .dimension = static_cast<bp::DimensionType>(0)};
    s.generator = bp::GeneratorType::OVERWORLD;
    s.game_type = bp::GameType::SURVIVAL;
    s.is_hardcore = false;
    s.game_difficulty = bp::Difficulty::NORMAL;
    s.default_spawn = {.x = 0, .y = 64, .z = 0};
    s.achievements_disabled = true;
    s.editor_world_type = bp::EditorWorldType::NON_EDITOR;
    s.is_created_in_editor = false;
    s.is_exported_from_editor = false;
    s.time = 0;
    s.education_edition_offer = bp::EducationEditionOffer::NONE;
    s.education_features_enabled = false;
    s.education_product_id = "";
    s.rain_level = 0.0f;
    s.lightning_level = 0.0f;
    s.confirmed_platform_locked_content = false;
    s.multiplayer_game_intent = true;
    s.lan_broadcast_intent = true;
    s.xbl_broadcast_intent = bp::GamePublishSetting::FRIENDS_ONLY;
    s.platform_broadcast_intent = bp::GamePublishSetting::FRIENDS_ONLY;
    s.commands_enabled = true;
    s.texture_packs_required = false;
    s.game_rules.push_back({.name = "dodaylightcycle", .can_be_modified_by_player = false, .value = true});
    s.experiments_previously_toggled = false;
    s.bonus_chest_enabled = false;
    s.start_with_map_enabled = false;
    s.default_permissions = bp::PlayerPermissionLevel::MEMBER;
    s.server_chunk_tick_range = 4;
    s.has_locked_behavior_pack = false;
    s.has_locked_resource_pack = false;
    s.is_from_locked_template = false;
    s.use_msa_gamertags_only = false;
    s.is_from_world_template = false;
    s.is_world_template_option_locked = false;
    s.spawn_v1_villagers = false;
    s.persona_disabled = false;
    s.custom_skins_disabled = false;
    s.emote_chat_muted = false;
    s.base_game_version = "1.21.0";
    s.limited_world_width = 0;
    s.limited_world_depth = 0;
    s.nether_type = bp::NetherWorldType::NORMAL;
    s.edu_shared_uri_resource = {.button_name = "", .link_uri = ""};
    s.override_force_experimental_gameplay = std::nullopt;
    s.chat_restriction_level = bp::ChatRestrictionLevel::NONE;
    s.disable_player_interactions = false;

    packet.level_id = "lvl";
    packet.level_name = "world";
    packet.template_content_identity = "";
    packet.is_trial = false;
    packet.movement_settings = {.rewind_history_size = 40, .server_authoritative_block_breaking = false};
    packet.level_current_time = 100;
    packet.enchantment_seed = 0;
    packet.multiplayer_correlation_id = "";
    packet.enable_item_stack_net_manager = true;
    packet.server_version = "1.21.0";
    packet.server_block_type_registry_checksum = 0;
    packet.world_template_id = {};
    packet.server_enabled_client_side_generation = false;
    packet.block_network_ids_are_hashes = true;
    packet.network_permissions = {.server_auth_sound_enabled = false};
    packet.server_configuration_join_info = std::nullopt;
    packet.server_telemetry_data = {};
}

TEST_CASE("start-game v975 form round-trips against the golden")
{
    using Packet = bp::StartGamePacket_<bp::ProtocolVersion::V975>;

    Packet packet;
    fill(packet);
    REQUIRE(encode(packet) == golden_v975);

    bp::BinaryReader reader{golden_v975};
    auto back = bp::Serializer<Packet>::deserialize(reader);
    REQUIRE(back.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    REQUIRE(back->settings.seed == 7);
    REQUIRE(back->settings.game_rules.size() == 1);
    REQUIRE(std::get<1>(back->settings.game_rules[0].value) == true);
    REQUIRE(back->level_name == "world");
}

// 995 added is_chat_logging and 997 added the two editor fields; nothing else moved,
// so the 1001 body is the 975 body plus three bytes.
TEST_CASE("start-game v1001 adds exactly the 995 and 997 fields")
{
    using Packet = bp::StartGamePacket_<bp::ProtocolVersion::V1001>;

    Packet packet;
    fill(packet);
    packet.settings.server_editor_connection_policy = bp::ServerEditorConnectionPolicy::MATCH_WORLD_TYPE;
    packet.settings.allow_anonymous_block_drops_in_editor_worlds = false;
    packet.is_chat_logging = false;

    const std::string encoded = encode(packet);
    REQUIRE(encoded.size() == golden_v975.size() + 3);

    bp::BinaryReader reader{encoded};
    auto back = bp::Serializer<Packet>::deserialize(reader);
    REQUIRE(back.has_value());
    REQUIRE(reader.getUnreadLength() == 0);
    REQUIRE(back->settings.seed == 7);
    REQUIRE(back->level_name == "world");
    REQUIRE(back->is_chat_logging == false);
}
