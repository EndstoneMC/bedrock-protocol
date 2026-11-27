"""Packets and types relating to level settings, world clocks and position tracking."""

from enum import IntEnum
from typing import Literal

from protocol import field, int16, int32, packet, type, uint8, uint32, uint64, uvarint32, uvarint64, value, varint32
from protocol.command import PlayerPermissionLevel
from protocol.common import BlockPos, DimensionType
from protocol.editor import EditorLevelMigrationVersion, ServerEditorConnectionPolicy, WorldType
from protocol.nbt import CompoundTag
from protocol.network import GamePublishSetting, NetworkBlockPosition

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"
go_package = "github.com/EndstoneMC/bedrock-protocol/go/protocol"


class GameType(IntEnum, int32):
    UNDEFINED = -1
    SURVIVAL = 0
    CREATIVE = 1
    ADVENTURE = 2
    DEFAULT = 5
    SPECTATOR = 6
    WORLD_DEFAULT = value(0, synonym=True)


class Difficulty(IntEnum, int32):
    PEACEFUL = 0
    EASY = 1
    NORMAL = 2
    HARD = 3
    COUNT = 4
    UNKNOWN = 5


class GeneratorType(IntEnum, int32):
    LEGACY = 0
    OVERWORLD = 1
    FLAT = 2
    NETHER = 3
    THE_END = 4
    VOID = 5
    UNDEFINED = 6


class NetherWorldType(IntEnum, bool):
    NORMAL = 0
    FLAT = 1


class SpawnBiomeType(IntEnum, int16):
    DEFAULT = 0
    USER_DEFINED = 1


class EducationEditionOffer(IntEnum, uint32):
    NONE = 0
    REST_OF_WORLD = 1
    CHINA_DEPRECATED = value(2, deprecated=True)


class ChatRestrictionLevel(IntEnum, uint8):
    NONE = 0
    DROPPED = 1
    DISABLED = 2


class SpawnSettings:
    type: SpawnBiomeType = field(type=int16)
    user_defined_biome_name: str
    dimension: DimensionType


@type(until=844)
class GameRulesChangedPacketData:
    rules: list[GameRule] = field(cereal=False)


@type(since=844)
class GameRulesChangedPacketData:
    rules: list[GameRule]


class ExperimentToggle:
    name: str
    enabled: bool


class Experiments:
    toggles: list[ExperimentToggle] = field(prefix=uint32)
    experiments_ever_toggled: bool


@type(until=944)
class LevelSettings:
    seed: uint64
    spawn_settings: SpawnSettings
    generator: GeneratorType
    game_type: GameType
    is_hardcore: bool = field(since=671)
    game_difficulty: Difficulty
    default_spawn: NetworkBlockPosition
    achievements_disabled: bool
    editor_world_type: WorldType
    is_created_in_editor: bool
    is_exported_from_editor: bool
    time: varint32
    education_edition_offer: EducationEditionOffer = field(type=varint32)
    education_features_enabled: bool
    education_product_id: str
    rain_level: float
    lightning_level: float
    confirmed_platform_locked_content: bool
    multiplayer_game_intent: bool
    lan_broadcast_intent: bool
    xbl_broadcast_intent: GamePublishSetting
    platform_broadcast_intent: GamePublishSetting
    commands_enabled: bool
    texture_packs_required: bool
    game_rules: list[GameRule] = field(cereal=False)
    experiments: list[ExperimentToggle] = field(prefix=uint32)
    experiments_ever_toggled: bool
    bonus_chest_enabled: bool
    start_with_map_enabled: bool
    default_permissions: PlayerPermissionLevel = field(type=varint32)
    server_chunk_tick_range: int32
    has_locked_behavior_pack: bool
    has_locked_resource_pack: bool
    is_from_locked_template: bool
    use_msa_gamertags_only: bool
    is_from_world_template: bool
    is_world_template_option_locked: bool
    spawn_v1_villagers: bool
    persona_disabled: bool
    custom_skins_disabled: bool
    emote_chat_muted: bool
    base_game_version: str
    limited_world_width: int32
    limited_world_depth: int32
    nether_type: NetherWorldType
    edu_shared_uri_resource: EduSharedUriResource
    override_force_experimental_gameplay_flag: bool
    chat_restriction_level: ChatRestrictionLevel
    disable_player_interactions: bool
    with field(since=685, until=924):
        server_id: str
        world_id: str
        scenario_id: str
        owner_id: str = field(since=818)


@type(since=944, until=2168)
class LevelSettings:
    seed: uint64
    spawn_settings: SpawnSettings
    generator: GeneratorType
    game_type: GameType
    is_hardcore: bool
    game_difficulty: Difficulty
    default_spawn: BlockPos
    achievements_disabled: bool
    editor_world_type: WorldType
    is_created_in_editor: bool
    is_exported_from_editor: bool
    time: varint32
    education_edition_offer: EducationEditionOffer = field(type=varint32)
    education_features_enabled: bool
    education_product_id: str
    rain_level: float
    lightning_level: float
    confirmed_platform_locked_content: bool
    multiplayer_game_intent: bool
    lan_broadcast_intent: bool
    xbl_broadcast_intent: GamePublishSetting
    platform_broadcast_intent: GamePublishSetting
    commands_enabled: bool
    texture_packs_required: bool
    game_rules: list[GameRule] = field(cereal=False)
    experiments: list[ExperimentToggle] = field(prefix=uint32)
    experiments_ever_toggled: bool
    bonus_chest_enabled: bool
    start_with_map_enabled: bool
    default_permissions: PlayerPermissionLevel = field(type=varint32)
    server_chunk_tick_range: int32
    has_locked_behavior_pack: bool
    has_locked_resource_pack: bool
    is_from_locked_template: bool
    use_msa_gamertags_only: bool
    is_from_world_template: bool
    is_world_template_option_locked: bool
    spawn_v1_villagers: bool
    persona_disabled: bool
    custom_skins_disabled: bool
    emote_chat_muted: bool
    base_game_version: str
    limited_world_width: int32
    limited_world_depth: int32
    nether_type: NetherWorldType
    edu_shared_uri_resource: EduSharedUriResource
    override_force_experimental_gameplay_flag: bool
    chat_restriction_level: ChatRestrictionLevel
    disable_player_interactions: bool
    with field(since=1001):
        server_editor_connection_policy: ServerEditorConnectionPolicy
        allow_anonymous_block_drops_in_editor_worlds: bool


@type(since=2168)
class LevelSettings:
    seed: uint64
    spawn_settings: SpawnSettings
    generator: GeneratorType
    game_type: GameType
    is_hardcore: bool
    game_difficulty: Difficulty
    default_spawn: BlockPos
    achievements_disabled: bool
    editor_world_type: WorldType
    is_created_in_editor: bool
    is_exported_from_editor: bool
    editor_level_migration_version: EditorLevelMigrationVersion = field(since=2225)
    time: varint32
    education_edition_offer: EducationEditionOffer
    education_features_enabled: bool
    education_product_id: str
    rain_level: float
    lightning_level: float
    confirmed_platform_locked_content: bool
    multiplayer_game_intent: bool
    lan_broadcast_intent: bool
    xbl_broadcast_intent: GamePublishSetting
    platform_broadcast_intent: GamePublishSetting
    commands_enabled: bool
    texture_packs_required: bool
    game_rules: GameRulesChangedPacketData
    experiments: Experiments
    bonus_chest_enabled: bool
    start_with_map_enabled: bool
    default_permissions: PlayerPermissionLevel
    server_chunk_tick_range: int32
    has_locked_behavior_pack: bool
    has_locked_resource_pack: bool
    is_from_locked_template: bool
    use_msa_gamertags_only: bool
    is_from_world_template: bool
    is_world_template_option_locked: bool
    spawn_v1_villagers: bool
    persona_disabled: bool
    custom_skins_disabled: bool
    emote_chat_muted: bool
    base_game_version: str
    limited_world_width: int32
    limited_world_depth: int32
    nether_type: NetherWorldType
    edu_shared_uri_resource: EduSharedUriResource
    override_force_experimental_gameplay_flag: bool | None
    chat_restriction_level: ChatRestrictionLevel
    disable_player_interactions: bool
    server_editor_connection_policy: ServerEditorConnectionPolicy
    allow_anonymous_block_drops_in_editor_worlds: bool


@packet(id=10)
class SetTimePacket:
    time: varint32


class SyncWorldClockStateData:
    clock_id: uvarint64
    time: varint32
    is_paused: bool


class TimeMarkerData:
    id: uvarint64
    name: str
    time: varint32
    period: int32 | None


class WorldClockData:
    id: uvarint64
    name: str
    time: varint32
    is_paused: bool
    time_markers: list[TimeMarkerData]


@packet(id=344, since=944)
class SyncWorldClocksPacket:
    class SyncStateData:
        clock_data: list[SyncWorldClockStateData]

    class InitializeRegistryData:
        clock_data: list[WorldClockData]

    class AddTimeMarkerData:
        clock_id: uvarint64
        time_markers: list[TimeMarkerData]

    class RemoveTimeMarkerData:
        clock_id: uvarint64
        time_marker_ids: list[uvarint64]

    data: SyncStateData | InitializeRegistryData | AddTimeMarkerData | RemoveTimeMarkerData


type PositionTrackingId = varint32


@packet(id=153)
class PositionTrackingDBServerBroadcastPacket:
    class Action(IntEnum, uint8):
        UPDATE = 0
        DESTROY = 1
        NOT_FOUND = 2

    action: Action
    id: PositionTrackingId
    data: CompoundTag


@packet(id=154)
class PositionTrackingDBClientRequestPacket:
    class Action(IntEnum, uint8):
        QUERY = 0

    action: Action
    id: PositionTrackingId


class EduSharedUriResource:
    button_name: str
    link_uri: str


class AgentCapabilities:
    can_modify_blocks: bool | None


class EducationLocalLevelSettings:
    code_builder_override_uri: str | None


class ExternalLinkSettings:
    url: str
    display_name: str


class EducationLevelSettings:
    code_builder_default_uri: str
    code_builder_title: str
    can_resize_code_builder: bool
    disable_legacy_title_bar: bool
    post_process_filter: str
    screenshot_border_resource_path: str
    agent_capabilities: AgentCapabilities | None
    local_settings: EducationLocalLevelSettings
    _deprecated: Literal[False]
    external_link_settings: ExternalLinkSettings | None


class GameRule:
    name: str
    can_be_modified_by_player: bool
    value: None | bool | uvarint32 | float = field(until=844)
    value: None | bool | int32 | float = field(since=844)


@type(cereal=False, until=2168)
class GameRule:
    name: str
    can_be_modified_by_player: bool
    value: None | bool | varint32 | float
