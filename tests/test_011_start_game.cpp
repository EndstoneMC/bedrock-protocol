#include <cstdint>
#include <string>

#include <bedrock/protocol/actor.h>
#include <bedrock/protocol/attributes.h>
#include <bedrock/protocol/game.h>

#include "fixture.hpp"

namespace {

// StartGamePacket is still hand-written at 1001, so protocol-docs cannot describe
// it: r26_u3 IS network version 1001 and carries no StartGamePacket.json. The
// cerealised form arrives at 2168, where the dump does describe it; gophertunnel is
// the wire for these two eras.
//
// Both oracles were run with one bool rule, the one rule kind the two eras write
// alike, so the integer rule below and its bytes were added by hand from the pair
// gophertunnel keeps apart as GameRuleLegacy and GameRule. A live 1.26.40 client
// accepts the result; it rejects the packet without it.
template <class Packet>
void fill(Packet &packet)
{
    packet.entity_id = bp::ActorUniqueID{1};
    packet.runtime_id = bp::ActorRuntimeID{2};
    packet.entity_game_type = bp::GameType::SURVIVAL;
    packet.pos = {.x = 1.0f, .y = 2.0f, .z = 3.0f};
    packet.rot = {.x = 4.0f, .y = 5.0f};

    auto &s = packet.settings;
    s.seed = 7;
    s.spawn_settings = {.type = bp::SpawnBiomeType::DEFAULT,
                        .user_defined_biome_name = "",
                        .dimension = bp::DimensionType{0}};
    s.generator = bp::GeneratorType::OVERWORLD;
    s.game_type = bp::GameType::SURVIVAL;
    s.is_hardcore = false;
    s.game_difficulty = bp::Difficulty::NORMAL;
    s.default_spawn = {.x = 0, .y = 64, .z = 0};
    s.achievements_disabled = true;
    s.editor_world_type = bp::WorldType::NON_EDITOR;
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
    // An integer rule, whose value is the one part of a rule the two eras write differently.
    s.game_rules.push_back(
        {.name = "maxcommandchainlength", .can_be_modified_by_player = false, .value = std::uint32_t{131070}});
    s.experiments_ever_toggled = false;
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
    packet.movement_settings = {.rewind_history_size = 40, .server_auth_block_breaking = false};
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

void fill_v2168(bp::StartGamePacket_<2168> &packet)
{
    packet.entity_id = bp::ActorUniqueID{1};
    packet.runtime_id = bp::ActorRuntimeID{2};
    packet.entity_game_type = bp::GameType::SURVIVAL;
    packet.pos = {.x = 1.0f, .y = 2.0f, .z = 3.0f};
    packet.rot = {.x = 4.0f, .y = 5.0f};

    auto &s = packet.settings;
    s.seed = 7;
    s.spawn_settings = {.type = bp::SpawnBiomeType::DEFAULT,
                        .user_defined_biome_name = "",
                        .dimension = bp::DimensionType{0}};
    s.generator = bp::GeneratorType::OVERWORLD;
    s.game_type = bp::GameType::SURVIVAL;
    s.is_hardcore = false;
    s.game_difficulty = bp::Difficulty::NORMAL;
    s.default_spawn = {.x = 0, .y = 64, .z = 0};
    s.achievements_disabled = true;
    s.editor_world_type = bp::WorldType::NON_EDITOR;
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
    s.rule_data.rules.push_back({.name = "dodaylightcycle", .can_be_modified_by_player = false, .value = true});
    // An integer rule, whose value is the one part of a rule the two eras write differently.
    s.rule_data.rules.push_back(
        {.name = "maxcommandchainlength", .can_be_modified_by_player = false, .value = std::int32_t{131070}});
    s.experiments = {.toggles = {}, .experiments_ever_toggled = false};
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
    s.server_editor_connection_policy = bp::ServerEditorConnectionPolicy::MATCH_WORLD_TYPE;
    s.allow_anonymous_block_drops_in_editor_worlds = false;

    packet.level_id = "lvl";
    packet.level_name = "world";
    packet.template_content_identity = "";
    packet.is_trial = false;
    packet.movement_settings = {.rewind_history_size = 40, .server_auth_block_breaking = false};
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

}  // namespace

TEST_CASE("StartGamePacket: id")
{
    STATIC_REQUIRE(bp::StartGamePacket_<975>::Id == 11);
    STATIC_REQUIRE(bp::StartGamePacket_<1001>::Id == 11);
    STATIC_REQUIRE(bp::StartGamePacket_<2168>::Id == 11);
}

TEST_CASE("StartGamePacket: v1001 round-trip")
{
    using Packet = bp::StartGamePacket_<1001>;

    Packet pkt;
    fill(pkt);
    pkt.settings.server_editor_connection_policy = bp::ServerEditorConnectionPolicy::MATCH_WORLD_TYPE;
    pkt.settings.allow_anonymous_block_drops_in_editor_worlds = false;
    pkt.is_logging_chat = false;

    // generated by gophertunnel:
    // packet.StartGame{EntityUniqueID: 1, EntityRuntimeID: 2, PlayerGameMode: 0,
    //   PlayerPosition: {1, 2, 3}, Pitch: 4, Yaw: 5, WorldSeed: 7, Dimension: 0, Generator: 1,
    //   WorldGameMode: 0, Difficulty: 2, WorldSpawn: {0, 64, 0}, AchievementsDisabled: true,
    //   MultiPlayerGame: true, LANBroadcastEnabled: true, XBLBroadcastMode: 2,
    //   PlatformBroadcastMode: 2, CommandsEnabled: true,
    //   GameRules: []protocol.GameRule{{Name: "dodaylightcycle", Value: true},
    //     {Name: "maxcommandchainlength", Value: uint32(131070)}},
    //   PlayerPermissions: 1, ServerChunkTickRadius: 4, BaseGameVersion: "1.21.0",
    //   LevelID: "lvl", WorldName: "world",
    //   PlayerMovementSettings: {RewindHistorySize: 40}, Time: 100,
    //   ServerAuthoritativeInventory: true, GameVersion: "1.21.0",
    //   PropertyData: map[string]any{}, UseBlockNetworkIDHashes: true}
    const std::string golden = bytes({
    0x02, 0x02, 0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00,
    0x00, 0x40, 0x40, 0x00, 0x00, 0x80, 0x40, 0x00, 0x00, 0xA0, 0x40, 0x07,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02,
    0x00, 0x00, 0x04, 0x00, 0x80, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x01, 0x01, 0x04, 0x04, 0x01, 0x00, 0x02, 0x0F, 0x64, 0x6F, 0x64, 0x61,
    0x79, 0x6C, 0x69, 0x67, 0x68, 0x74, 0x63, 0x79, 0x63, 0x6C, 0x65, 0x00,
    0x01, 0x01, 0x15, 0x6D, 0x61, 0x78, 0x63, 0x6F, 0x6D, 0x6D, 0x61, 0x6E,
    0x64, 0x63, 0x68, 0x61, 0x69, 0x6E, 0x6C, 0x65, 0x6E, 0x67, 0x74, 0x68,
    0x00, 0x02, 0xFE, 0xFF, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x02, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x06, 0x31, 0x2E, 0x32, 0x31, 0x2E, 0x30, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x03, 0x6C, 0x76, 0x6C, 0x05, 0x77, 0x6F, 0x72, 0x6C, 0x64,
    0x00, 0x00, 0x50, 0x00, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x01, 0x06, 0x31, 0x2E, 0x32, 0x31, 0x2E, 0x30, 0x0A,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
});

    REQUIRE(encode(pkt) == golden);

    const auto rt = decode<Packet>(golden);
    REQUIRE(rt.settings.seed == 7);
    REQUIRE(rt.settings.game_rules.size() == 2);
    REQUIRE(std::get<1>(rt.settings.game_rules[0].value) == true);
    REQUIRE(std::get<2>(rt.settings.game_rules[1].value) == 131070);
    REQUIRE(rt.level_name == "world");
    REQUIRE(rt.is_logging_chat == false);
}

// 995 added is_logging_chat and 997 the two editor fields; nothing else moved, so
// the 975 body is the 1001 one minus exactly those three bytes.
TEST_CASE("StartGamePacket: v975 is the v1001 body less the 995 and 997 fields")
{
    using Packet = bp::StartGamePacket_<975>;

    Packet pkt;
    fill(pkt);
    const auto encoded = encode(pkt);

    using Packet1001 = bp::StartGamePacket_<1001>;
    Packet1001 newer;
    fill(newer);
    newer.settings.server_editor_connection_policy = bp::ServerEditorConnectionPolicy::MATCH_WORLD_TYPE;
    newer.settings.allow_anonymous_block_drops_in_editor_worlds = false;
    newer.is_logging_chat = false;
    REQUIRE(encoded.size() + 3 == encode(newer).size());

    const auto rt = decode<Packet>(encoded);
    REQUIRE(rt.settings.seed == 7);
    REQUIRE(rt.level_name == "world");
}

TEST_CASE("StartGamePacket: v2168 round-trip")
{
    using Packet = bp::StartGamePacket_<2168>;

    Packet pkt;
    fill_v2168(pkt);

    // generated by CloudburstMC Bedrock_v2168:
    // StartGamePacket{uniqueEntityId: 1, runtimeEntityId: 2, playerGameType: SURVIVAL,
    //   playerPosition: (1, 2, 3), rotation: (4, 5), seed: 7, spawnBiomeType: DEFAULT,
    //   customBiomeName: "", dimensionId: 0, generatorId: 1, levelGameType: SURVIVAL,
    //   difficulty: 2, defaultSpawn: (0, 64, 0), achievementsDisabled: true,
    //   editorWorldType: NON_EDITOR, multiplayerGame: true, broadcastingToLan: true,
    //   xblBroadcastMode: FRIENDS_ONLY, platformBroadcastMode: FRIENDS_ONLY,
    //   commandsEnabled: true, gamerules: [GameRuleData("dodaylightcycle", false, true),
    //     GameRuleData("maxcommandchainlength", false, 131070)],
    //   defaultPlayerPermission: MEMBER, serverChunkTickRange: 4, vanillaVersion: "1.21.0",
    //   eduSharedUriResource: EMPTY, forceExperimentalGameplay: empty,
    //   chatRestrictionLevel: NONE, serverEditorConnectionPolicy: 0, levelId: "lvl",
    //   levelName: "world", premiumWorldTemplateId: "", rewindHistorySize: 40,
    //   currentTick: 100, multiplayerCorrelationId: "", inventoriesServerAuthoritative: true,
    //   serverEngine: "1.21.0", playerPropertyData: NbtMap.EMPTY, blockRegistryChecksum: 0,
    //   worldTemplateId: 0-0, blockNetworkIdsHashed: true,
    //   networkPermissions: DEFAULT, serverConfigurationJoinInfo: null,
    //   serverId: "", scenarioId: "", worldId: "", ownerId: ""}
    const std::string golden = bytes({
    0x02, 0x02, 0x00, 0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x00, 0x40, 0x00,
    0x00, 0x40, 0x40, 0x00, 0x00, 0x80, 0x40, 0x00, 0x00, 0xA0, 0x40, 0x07,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02,
    0x00, 0x00, 0x04, 0x00, 0x80, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x01, 0x01, 0x04, 0x04, 0x01, 0x00, 0x02, 0x0F, 0x64, 0x6F, 0x64, 0x61,
    0x79, 0x6C, 0x69, 0x67, 0x68, 0x74, 0x63, 0x79, 0x63, 0x6C, 0x65, 0x00,
    0x01, 0x01, 0x15, 0x6D, 0x61, 0x78, 0x63, 0x6F, 0x6D, 0x6D, 0x61, 0x6E,
    0x64, 0x63, 0x68, 0x61, 0x69, 0x6E, 0x6C, 0x65, 0x6E, 0x67, 0x74, 0x68,
    0x00, 0x02, 0xFE, 0xFF, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x01, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x06, 0x31, 0x2E, 0x32, 0x31, 0x2E, 0x30, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x03, 0x6C, 0x76, 0x6C, 0x05, 0x77, 0x6F, 0x72, 0x6C,
    0x64, 0x00, 0x00, 0x50, 0x00, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x01, 0x06, 0x31, 0x2E, 0x32, 0x31, 0x2E, 0x30,
    0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
});

    REQUIRE(encode(pkt) == golden);

    const auto rt = decode<Packet>(golden);
    REQUIRE(rt.settings.seed == 7);
    REQUIRE(rt.settings.rule_data.rules.size() == 2);
    REQUIRE(std::get<1>(rt.settings.rule_data.rules[0].value) == true);
    REQUIRE(std::get<2>(rt.settings.rule_data.rules[1].value) == 131070);
    REQUIRE(rt.settings.experiments.toggles.empty());
    REQUIRE(rt.settings.experiments.experiments_ever_toggled == false);
    REQUIRE(rt.settings.default_permissions == bp::PlayerPermissionLevel::MEMBER);
    REQUIRE(rt.level_name == "world");
    REQUIRE(rt.block_properties.empty());
}

// The cerealisation dropped is_logging_chat, narrowed default_permissions from a
// varint32 to its int8 underlying, and widened an integer rule's value to a fixed
// uint32. The last two cancel in length, so with this world's rules the two bodies
// come out the same size and are a wire break all the same. Nothing about a body's
// length says which era wrote it, which is why the integer rule is worth carrying:
// without one the older body still reads as the newer, holding the wrong values.
TEST_CASE("StartGamePacket: a v1001 body does not decode as a v2168 one")
{
    using Packet1001 = bp::StartGamePacket_<1001>;

    Packet1001 older;
    fill(older);
    older.settings.server_editor_connection_policy = bp::ServerEditorConnectionPolicy::MATCH_WORLD_TYPE;
    older.settings.allow_anonymous_block_drops_in_editor_worlds = false;
    older.is_logging_chat = false;

    bp::StartGamePacket_<2168> newer;
    fill_v2168(newer);

    const auto old_bytes = encode(older);
    const auto new_bytes = encode(newer);
    REQUIRE(old_bytes.size() == new_bytes.size());
    REQUIRE(old_bytes != new_bytes);

    REQUIRE(rejects<bp::StartGamePacket_<2168>>(old_bytes));
    REQUIRE(rejects<bp::StartGamePacket_<1001>>(new_bytes));
}
