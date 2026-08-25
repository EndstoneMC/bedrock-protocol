import uuid
from enum import IntEnum

from protocol import field, int8, int16, int32, packet, type, uint8, uint32, uint64, uvarint32, varint32
from protocol.actor import ActorRuntimeID, ActorUniqueID
from protocol.attributes import DimensionType
from protocol.common import BlockPos, Vec2, Vec3
from protocol.edu import EduSharedUriResource
from protocol.nbt import CompoundTag
from protocol.presence import ServerConfigurationJoinInfo, ServerTelemetryData

package = "bedrock.protocol"


class GameType(IntEnum):
    UNDEFINED = -1
    SURVIVAL = 0
    CREATIVE = 1
    ADVENTURE = 2
    DEFAULT = 5
    SPECTATOR = 6


class Difficulty(IntEnum):
    PEACEFUL = 0
    EASY = 1
    NORMAL = 2
    HARD = 3
    COUNT = 4
    UNKNOWN = 5


class GeneratorType(IntEnum):
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


class WorldType(IntEnum):
    NON_EDITOR = 0
    EDITOR_PROJECT = 1
    EDITOR_TEST_LEVEL = 2
    EDITOR_REALMS_UPLOAD = 3


class EducationEditionOffer(IntEnum, uint32):
    NONE = 0
    REST_OF_WORLD = 1
    CHINA_DEPRECATED = 2


class GamePublishSetting(IntEnum):
    NO_MULTI_PLAY = 0
    INVITE_ONLY = 1
    FRIENDS_ONLY = 2
    FRIENDS_OF_FRIENDS = 3
    PUBLIC = 4


class PlayerPermissionLevel(IntEnum, int8):
    VISITOR = 0
    MEMBER = 1
    OPERATOR = 2
    CUSTOM = 3


class ChatRestrictionLevel(IntEnum, uint8):
    NONE = 0
    DROPPED = 1
    DISABLED = 2


class ServerEditorConnectionPolicy(IntEnum):
    MATCH_WORLD_TYPE = 0
    EDITOR_ONLY = 1
    VANILLA_ONLY = 2
    MIXED = 3


class SpawnSettings:
    type: SpawnBiomeType = field(type=int16)
    user_defined_biome_name: str
    dimension: DimensionType


class GameRule:
    name: str
    can_be_modified_by_player: bool
    value: None | bool | int32 | float


@type(cereal=False, until=2168)
class GameRule:
    """The shape StartGame wrote before it cerealised at 2168, with the integer
    case as a varint; packet 72 wrote the fixed one throughout."""

    name: str
    can_be_modified_by_player: bool
    value: None | bool | uvarint32 | float


class GameRulesChangedPacketData:
    rules: list[GameRule]


class ExperimentToggle:
    name: str
    enabled: bool


class Experiments:
    toggles: list[ExperimentToggle] = field(prefix=uint32)
    experiments_ever_toggled: bool


class SyncedPlayerMovementSettings:
    rewind_history_size: varint32
    server_auth_block_breaking: bool


class NetworkPermissions:
    server_auth_sound_enabled: bool


class BlockEntry:
    name: str
    properties: CompoundTag


@type(since=2168)
class ServerBlockProperty:
    name: str
    tag: CompoundTag


@type(until=2168)
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
    override_force_experimental_gameplay: bool | None
    chat_restriction_level: ChatRestrictionLevel
    disable_player_interactions: bool
    server_editor_connection_policy: ServerEditorConnectionPolicy = field(since=1001)
    allow_anonymous_block_drops_in_editor_worlds: bool = field(since=1001)


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
    rule_data: GameRulesChangedPacketData
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
    override_force_experimental_gameplay: bool | None
    chat_restriction_level: ChatRestrictionLevel
    disable_player_interactions: bool
    server_editor_connection_policy: ServerEditorConnectionPolicy
    allow_anonymous_block_drops_in_editor_worlds: bool


@packet(id=11, until=2168)
class StartGamePacket:
    entity_id: ActorUniqueID
    runtime_id: ActorRuntimeID
    entity_game_type: GameType
    pos: Vec3
    rot: Vec2
    settings: LevelSettings
    level_id: str
    level_name: str
    template_content_identity: str
    is_trial: bool
    movement_settings: SyncedPlayerMovementSettings
    level_current_time: uint64
    enchantment_seed: varint32
    block_properties: list[BlockEntry]
    multiplayer_correlation_id: str
    enable_item_stack_net_manager: bool
    server_version: str
    player_property_data: CompoundTag
    server_block_type_registry_checksum: uint64
    world_template_id: uuid.UUID
    server_enabled_client_side_generation: bool
    block_network_ids_are_hashes: bool
    network_permissions: NetworkPermissions
    is_logging_chat: bool = field(since=1001)
    server_configuration_join_info: ServerConfigurationJoinInfo | None
    server_telemetry_data: ServerTelemetryData


@packet(id=72)
class GameRulesChangedPacket:
    rule_data: GameRulesChangedPacketData


@packet(id=11, since=2168)
class StartGamePacket:
    entity_id: ActorUniqueID
    runtime_id: ActorRuntimeID
    entity_game_type: GameType
    pos: Vec3
    rot: Vec2
    settings: LevelSettings
    level_id: str
    level_name: str
    template_content_identity: str
    is_trial: bool
    movement_settings: SyncedPlayerMovementSettings
    level_current_time: uint64
    enchantment_seed: varint32
    block_properties: list[ServerBlockProperty]
    multiplayer_correlation_id: str
    enable_item_stack_net_manager: bool
    server_version: str
    player_property_data: CompoundTag
    server_block_type_registry_checksum: uint64
    world_template_id: uuid.UUID
    server_enabled_client_side_generation: bool
    block_network_ids_are_hashes: bool
    network_permissions: NetworkPermissions
    server_configuration_join_info: ServerConfigurationJoinInfo | None
    server_telemetry_data: ServerTelemetryData


@packet(id=10, since=2168)
class SetTimePacket:
    time: varint32


@packet(id=59, since=2168)
class SetCommandsEnabledPacket:
    commands_enabled: bool
