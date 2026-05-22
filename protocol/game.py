import uuid
from enum import IntEnum, auto

from protocol import (
    field,
    int16,
    int32,
    packet,
    type,
    uint8,
    uint32,
    uint64,
    uvarint32,
    varint32,
)
from protocol.actor import ActorRuntimeID, ActorUniqueID
from protocol.common import BlockPos, Vec2, Vec3
from protocol.nbt import CompoundTag
from protocol.level import DimensionType

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
    COUNT = auto()
    UNKNOWN = auto()


class SpawnBiomeType(IntEnum):
    DEFAULT = 0
    USER_DEFINED = 1


@type(since=407)
class SpawnSettings:
    type: SpawnBiomeType = field(type=int16)
    user_defined_biome_name: str
    dimension: DimensionType


@type(since=465)
class EduSharedUriResource:
    button_name: str
    link_uri: str


class GameRule:
    class Type(IntEnum):
        INVALID = 0
        BOOL = 1
        INT = 2
        FLOAT = 3

    name: str
    can_be_modified_by_player: bool = field(since=671)
    value: bool | uvarint32 | float = field(tag=Type)


class GameRules:
    game_rules: list[GameRule]


@type(since=419)
class Experiments:
    experiment_data: list[tuple[str, bool]] = field(prefix=uint32)
    experiments_ever_toggled: bool


class LevelSettings:
    seed: varint32 = field(until=503)
    seed: uint64 = field(since=503)
    spawn_settings: SpawnSettings = field(since=407)
    generator: varint32
    game_type: GameType = field(type=varint32)
    is_hardcore: bool = field(since=671)
    game_difficulty: Difficulty = field(type=varint32)
    default_spawn: BlockPos
    achievements_disabled: bool
    editor_world_type: varint32 = field(since=671)
    is_created_in_editor: bool = field(since=582)
    is_exported_from_editor: bool = field(since=582)
    time: varint32
    education_edition_offer: varint32 = field(since=407)
    education_features_enabled: bool
    education_product_id: str = field(since=407)
    rain_level: float
    lightning_level: float
    confirmed_platform_locked_content: bool = field(since=332)
    multiplayer_game_intent: bool
    lan_broadcast_intent: bool
    xbl_broadcast_intent: varint32 = field(since=332)
    platform_broadcast_intent: varint32 = field(since=332)
    commands_enabled: bool
    texture_packs_required: bool
    game_rules: GameRules
    experiments: Experiments = field(since=419)
    bonus_chest_enabled: bool
    start_with_map_enabled: bool
    default_permissions: varint32
    server_chunk_tick_range: int32
    has_locked_behavior_pack: bool
    has_locked_resource_pack: bool
    is_from_locked_template: bool
    use_msa_gamertags_only: bool
    is_from_world_template: bool = field(since=313)
    is_world_template_option_locked: bool = field(since=332)
    spawn_v1_villagers: bool = field(since=361)
    persona_disabled: bool = field(since=544)
    custom_skins_disabled: bool = field(since=544)
    emote_chat_muted: bool = field(since=567)
    base_game_version: str = field(since=388)
    limited_world_width: int32 = field(since=407)
    limited_world_depth: int32 = field(since=407)
    nether_type: bool = field(since=407)
    edu_shared_uri_resource: EduSharedUriResource = field(since=465)
    override_force_experimental_gameplay_flag: bool | None = field(since=407)
    chat_restriction_level: uint8 = field(since=544)
    disable_player_interactions: bool = field(since=544)
    server_id: str = field(since=685, until=924)
    world_id: str = field(since=685, until=924)
    scenario_id: str = field(since=685, until=924)
    owner_id: str = field(since=818, until=924)


@type(since=428)
class SyncedPlayerMovementSettings:
    authoritative_movement_mode: varint32 = field(until=818)
    rewind_history_size: varint32
    server_authoritative_block_breaking: bool


@type(since=589)
class NetworkPermissions:
    server_auth_sound_enabled: bool


class ServerConfiguration:
    @type(since=924)
    class GatheringsConfigurationJoinInfo:
        experience_id: uuid.UUID
        experience_name: str
        experience_world_id: uuid.UUID
        experience_world_name: str
        creator_id: str
        target_id: uuid.UUID = field(since=944)
        scenario_id: str
        server_id: str

    @type(since=944)
    class PresenceConfiguration:
        experience_name: str
        world_name: str

    @type(since=944)
    class ClientStoreEntryPointConfiguration:
        store_id: str
        store_name: str


@type(since=924)
class ServerConfigurationJoinInfo:
    gatherings_configuration_join_info: (
        ServerConfiguration.GatheringsConfigurationJoinInfo | None
    )
    client_store_entrypoint_configuration: (
        ServerConfiguration.ClientStoreEntryPointConfiguration | None
    ) = field(since=944)
    presence_configuration: ServerConfiguration.PresenceConfiguration | None = field(
        since=944
    )


@type(since=924)
class ServerTelemetryData:
    server_id: str
    scenario_id: str
    world_id: str
    owner_id: str


@packet(id=11)
class StartGamePacket:
    entity_id: ActorUniqueID
    runtime_id: ActorRuntimeID
    entity_game_type: GameType = field(type=varint32)
    pos: Vec3
    rot: Vec2
    settings: LevelSettings
    level_id: str
    level_name: str
    template_content_identity: str
    is_trial: bool
    authoritative_movement_mode: bool = field(since=388, until=419)
    authoritative_movement_mode: varint32 = field(since=419, until=428)
    movement_settings: SyncedPlayerMovementSettings = field(since=428)
    level_current_time: uint64
    enchantment_seed: varint32
    block_properties: list[tuple[str, CompoundTag]] = field(since=388)
    multiplayer_correlation_id: str
    enable_item_stack_net_manager: bool = field(since=407)
    server_version: str = field(since=465)
    player_property_data: CompoundTag = field(since=527)
    server_block_type_registry_checksum: uint64 = field(since=475)
    world_template_id: uuid.UUID = field(since=527)
    server_enabled_client_side_generation: bool = field(since=544)
    block_network_ids_are_hashes: bool = field(since=582)
    tick_death_systems_enabled: bool = field(since=827, until=898)
    network_permissions: NetworkPermissions = field(since=589)
    server_configuration_join_info: ServerConfigurationJoinInfo | None = field(
        since=924
    )
    server_telemetry_data: ServerTelemetryData = field(since=924)
