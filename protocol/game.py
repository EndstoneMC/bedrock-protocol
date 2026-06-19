import uuid
from enum import IntEnum

from protocol import (
    field,
    int16,
    int32,
    int64,
    packet,
    type,
    uint8,
    uint16,
    uint32,
    uint64,
    uvarint32,
    uvarint64,
    value,
    varint32,
    varint64,
)
from protocol.actor import ActorRuntimeID, ActorUniqueID, CommandPermissionLevel
from protocol.common import BlockPos, NetworkBlockPos, Vec2, Vec3
from protocol.dimension import DimensionType, GeneratorType
from protocol.edu import EduSharedUriResource
from protocol.input import PlayerInputTick
from protocol.nbt import CompoundTag

package = "bedrock.protocol"

type LevelSeed64 = uint64


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


class NetherWorldType(IntEnum):
    NORMAL = 0
    FLAT = 1


class EducationEditionOffer(IntEnum):
    NONE = 0
    REST_OF_WORLD = 1
    CHINA = 2  # TODO: BDS marks this `China_Deprecated`; confirm the deprecation version


class EditorWorldType(IntEnum):
    NON_EDITOR = 0
    EDITOR_PROJECT = 1
    EDITOR_TEST_LEVEL = 2
    EDITOR_REALMS_UPLOAD = 3


class GamePublishSetting(IntEnum):
    NO_MULTI_PLAY = 0
    INVITE_ONLY = 1
    FRIENDS_ONLY = 2
    FRIENDS_OF_FRIENDS = 3
    PUBLIC = 4


class PlayerPermissionLevel(IntEnum):
    VISITOR = 0
    MEMBER = 1
    OPERATOR = 2
    CUSTOM = 3


class ChatRestrictionLevel(IntEnum):
    NONE = 0
    DROPPED = 1
    DISABLED = 2


class SpawnBiomeType(IntEnum):
    DEFAULT = 0
    USER_DEFINED = 1


@type(since=407)
class SpawnSettings:
    type: SpawnBiomeType = field(type=int16)
    user_defined_biome_name: str
    dimension: DimensionType


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


class Experiments:
    experiment_data: list[tuple[str, bool]] = field(prefix=uint32)


@type(since=419)
class ItemEntry:
    """Item registry entry sent in StartGame from v419..v775. Replaced by
    the dedicated ItemRegistryPacket at v776 (gating lives on the field)."""

    name: str
    runtime_id: int16
    component_based: bool


class LevelSettings:
    seed: varint32 = field(until=503)
    seed: LevelSeed64 = field(since=503)
    spawn_settings: SpawnSettings = field(since=407)
    generator: GeneratorType = field(type=varint32)
    game_type: GameType = field(type=uvarint32)
    is_hardcore: bool = field(since=671)
    game_difficulty: Difficulty = field(type=varint32)
    default_spawn: NetworkBlockPos = field(until=944)
    default_spawn: BlockPos = field(since=944)
    achievements_disabled: bool
    editor_world: bool = field(since=534, until=671)
    editor_world_type: EditorWorldType = field(type=varint32, since=671)
    is_created_in_editor: bool = field(since=582)
    is_exported_from_editor: bool = field(since=582)
    time: varint32
    education_edition_offer: bool = field(until=407)
    education_edition_offer: EducationEditionOffer = field(type=varint32, since=407)
    education_features_enabled: bool
    education_product_id: str = field(since=407)
    rain_level: float
    lightning_level: float
    confirmed_platform_locked_content: bool = field(since=332)
    multiplayer_game_intent: bool
    lan_broadcast_intent: bool
    xbl_broadcast_intent: GamePublishSetting = field(type=varint32, since=332)
    platform_broadcast_intent: GamePublishSetting = field(type=varint32, since=332)
    commands_enabled: bool
    texture_packs_required: bool
    game_rules: GameRules
    experiments: Experiments = field(since=419)
    experiments_previously_toggled: bool = field(since=419)
    bonus_chest_enabled: bool
    start_with_map_enabled: bool
    default_permissions: PlayerPermissionLevel = field(type=varint32)
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
    nether_type: NetherWorldType = field(type=uint8, since=407)
    edu_shared_uri_resource: EduSharedUriResource = field(since=465)
    override_force_experimental_gameplay_flag: bool | None = field(since=407)
    chat_restriction_level: ChatRestrictionLevel = field(type=uint8, since=544)
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

    @type(since=944, until=1001)
    class PresenceConfiguration:
        experience_name: str
        world_name: str

    @type(since=1001)
    class PresenceConfiguration:
        experience_name: str | None
        world_name: str | None
        rich_presence_id: str

    @type(since=944)
    class ClientStoreEntryPointConfiguration:
        store_id: str
        store_name: str


@type(since=924)
class ServerConfigurationJoinInfo:
    gatherings_configuration_join_info: ServerConfiguration.GatheringsConfigurationJoinInfo | None
    client_store_entrypoint_configuration: ServerConfiguration.ClientStoreEntryPointConfiguration | None = field(
        since=944
    )
    presence_configuration: ServerConfiguration.PresenceConfiguration | None = field(since=944)


@type(since=924)
class ServerTelemetryData:
    server_id: str
    scenario_id: str
    world_id: str
    owner_id: str


# Names from Mojang/bedrock-protocol-docs (AdventureSettingsPacket::Flags); the
# legacy AdventureSettingsPacket was removed before bedrock-headers' earliest
# branch (r21_u4) so the BDS C++ header is unavailable.
# TODO: confirm against BDS
class AdventureSettingsPacketFlags(IntEnum):
    WORLD_IMMUTABLE = 1 << 0
    NO_PVM = 1 << 1
    NO_MVP = 1 << 2
    SHOW_NAME_TAGS = 1 << 4
    AUTO_JUMP = 1 << 5
    PLAYER_MAY_FLY = 1 << 6
    PLAYER_NO_CLIP = 1 << 7
    PLAYER_WORLD_BUILDER = 1 << 8
    PLAYER_FLYING = 1 << 9
    PLAYER_MUTED = 1 << 10


# TODO: confirm against BDS -- the legacy AdventureSettingsPacket's second
# bitfield (action permissions) has no surviving source in bedrock-headers,
# EndstoneMC/protocol-docs, or Mojang/bedrock-protocol-docs. Bit positions
# follow AbilitiesIndex ordering but the enum's own BDS name is unverified.
class AdventureSettingsFlag2(IntEnum):
    MINE = 1 << 0
    DOORS_AND_SWITCHES = 1 << 1
    OPEN_CONTAINERS = 1 << 2
    ATTACK_PLAYERS = 1 << 3
    ATTACK_MOBS = 1 << 4
    OPERATOR = 1 << 5
    TELEPORT = 1 << 7
    BUILD = 1 << 8
    DEFAULT_LEVEL_PERMISSIONS = 1 << 9


@packet(id=55)
class AdventureSettingsPacket:
    flags1: uvarint32
    command_permission: CommandPermissionLevel = field(type=uvarint32)
    flags2: uvarint32
    player_permission: PlayerPermissionLevel = field(type=uvarint32)
    custom_flags: uvarint32
    entity_unique_id: int64


@packet(id=95)
class AutomationClientConnectPacket:
    """Initiates websocket connection"""

    ip: str


@packet(id=309, since=685)
class AwardAchievementPacket:
    achievement_id: int32


class AbilityLayer:
    """One layer of a LayeredAbilities snapshot, flattened so each ability becomes a bit in a
    pair of fixed-width bitmasks. abilities_set marks which bits this layer overrides;
    ability_values is the value of each such bit."""

    layer_type: uint16
    abilities_set: int32
    ability_values: int32
    fly_speed: float
    walk_speed: float


@packet(id=197, since=567)
class ClientCheatAbilityPacket:
    """Carries the same payload as UpdateAbilitiesPacket, sent from the server to instruct the
    client about its current cheat-related abilities."""

    target_player_id: ActorUniqueID = field(type=int64)
    player_permission: PlayerPermissionLevel = field(type=uint8)
    command_permission: CommandPermissionLevel = field(type=uint8)
    ability_layers: list[AbilityLayer]


@packet(id=171, since=465)
class CreatePhotoPacket:
    """Players now have the possibility to export photos from their portfolios into photo items in their inventory.
    EDU."""

    id: ActorUniqueID
    photo_name: str
    photo_item_name: str


@packet(id=189, since=534)
class DeathInfoPacket:
    """Sent from the server to client when player dies (Level::onPlayerDeath)."""

    cause_attack_name: str
    messages: list[str]


class LegacyTelemetryEventType(IntEnum):
    """Discriminator for LegacyTelemetryEventPacketPayload.mEventData."""

    ACHIEVEMENT = 0
    INTERACTION = 1
    PORTAL_CREATED = 2
    PORTAL_USED = 3
    MOB_KILLED = 4
    CAULDRON_USED = 5
    PLAYER_DIED = 6
    BOSS_KILLED = 7
    SLASH_COMMAND = 11
    MOB_BORN = 13
    POI_CAULDRON_USED = 15
    COMPOSTER_USED = 16
    BELL_USED = 17
    ACTOR_DEFINITION = 18
    RAID_UPDATE = 19
    TARGET_BLOCK_HIT = 23
    PIGLIN_BARTER = 24
    PLAYER_WAXED_OR_UNWAXED_COPPER = 25
    CODE_BUILDER_RUNTIME_ACTION = 26
    CODE_BUILDER_SCOREBOARD = 27
    ITEM_USED = 31


class AchievementEventData:
    achievement_id: varint32


class InteractionEventData:
    interaction_type: varint32
    interacted_entity_type: varint32
    interacted_entity_variant: varint32
    interacted_entity_color: uint8


class PortalCreatedEventData:
    built_in_dimension: DimensionType


class PortalUsedEventData:
    from_dimension: DimensionType
    to_dimension: DimensionType


class MobKilledEventData:
    killer_entity_id: varint64
    killed_mob_id: varint64
    damage_source: varint32
    trader_tier: varint32
    trader_name: str


class CauldronUsedEventData:
    contents_type: uvarint32
    contents_color: varint32
    fill_level: varint32


class PlayerDiedEventData:
    killer_id: varint32
    damage_source: varint32


class BossKilledEventData:
    boss_unique_id: ActorUniqueID
    party_size: varint32
    boss_type: varint32


class SlashCommandEventData:
    """The on-wire form folds error_count and error_list into the command-name + outputs join
    that CloudburstMC emits as ';'-separated."""

    success_count: varint32
    error_count: varint32
    command_name: str
    error_list: str


class MobBornEventData:
    """Sent in the v589+ codec; absent before that version."""

    baby_type: varint32
    baby_variant: varint32
    baby_color: uint8


class POICauldronUsedEventData:
    item_id: int32
    interaction_type: int32


class ComposterUsedEventData:
    item_id: int32
    interaction_type: int32


class BellUsedEventData:
    item_id: varint32


class ActorDefinitionEventData:
    event_name: str


class RaidUpdateEventData:
    current_wave: varint32
    total_waves: varint32
    success: bool


class TargetBlockHitEventData:
    redstone_level: varint32


class PiglinBarterEventData:
    item_id: varint32
    was_targeting_bartering_player: bool


class PlayerWaxedOrUnwaxedCopperEventData:
    block_id: varint32


class CodeBuilderRuntimeActionEventData:
    runtime_action: str


class CodeBuilderScoreboardEventData:
    objective_name: str
    score: varint32


class ItemUsedEventData:
    item_id: int32
    item_aux: int32
    use_method: int32
    count: int32


class EmptyEventData:
    pass


type LegacyTelemetryEventData = (
    AchievementEventData
    | InteractionEventData
    | PortalCreatedEventData
    | PortalUsedEventData
    | MobKilledEventData
    | CauldronUsedEventData
    | PlayerDiedEventData
    | BossKilledEventData
    | SlashCommandEventData
    | MobBornEventData
    | POICauldronUsedEventData
    | ComposterUsedEventData
    | BellUsedEventData
    | ActorDefinitionEventData
    | RaidUpdateEventData
    | TargetBlockHitEventData
    | PiglinBarterEventData
    | PlayerWaxedOrUnwaxedCopperEventData
    | CodeBuilderRuntimeActionEventData
    | CodeBuilderScoreboardEventData
    | ItemUsedEventData
    | EmptyEventData
)


@packet(id=65)
class EventPacket:
    """Sends telemetry events to the client so the client can then send that on to the eventing system."""

    player_unique_id: ActorUniqueID
    # COMPILER_EXTENSION_NEEDED: the wire layout is event_type (signed varint), use_player_id
    # bool, then variant body. The body shape depends on event_type (see the typed-union
    # alternatives above) but the tag is separated from the body by use_player_id, and the
    # v898 codec writes the tag a second time as a uvarint right before the body. The DSL has
    # no "split-tag" or "tag-prefix duplicated since=N" facility.
    event_type: LegacyTelemetryEventType = field(type=varint32)
    use_player_id: bool
    event_data_body: bytes = field(prefix=None)


class FeatureBinaryJsonFormat:
    feature_name: str
    binary_json_output: str


@packet(id=191, since=544)
class FeatureRegistryPacket:
    """This is the packet that tracks the active feature registry data from the server so that client can place the
    features themselves."""

    features_data: list[FeatureBinaryJsonFormat]


# FilterTextPacket (id=163, v422..v671) is omitted: removed before v975 and the
# DSL cannot express a lone @packet(until=) today.


@packet(id=72)
class GameRulesChangedPacket:
    """Updates game rules."""

    # bedrock-headers wraps the list in a GameRulesChangedPacketData (mRuleData) holding
    # std::vector<GameRule> mRules; on the wire this collapses to the same varuint32-prefixed
    # list, modeled directly here.
    rules: list[GameRule]


# CloudburstMC writes a flat block of TestParameters fields inline; the BDS
# header bundles them into gametest::TestParameters but the wire is the
# same flat sequence.
class TestParameters:
    max_tests_per_batch: varint32
    repeat_count: varint32
    rotation: uint8
    stop_on_failure: bool
    test_pos: BlockPos
    tests_per_row: varint32


@packet(id=194, since=554)
class GameTestRequestPacket:
    """Internal Text Packet."""

    params: TestParameters
    test_name: str


@packet(id=195, since=554)
class GameTestResultsPacket:
    """Game Test Results Packet."""

    succeeded: bool
    error: str
    test_name: str


@type(until=776)
class SimpleItemDefinition:
    name: str
    component_data: CompoundTag


@type(since=776)
class SimpleItemDefinition:
    name: str
    runtime_id: int16
    component_based: bool
    version: varint32
    component_data: CompoundTag


@packet(id=162, since=419)
class ItemComponentPacket:
    items: list[SimpleItemDefinition]


class MultiplayerSettingsPacketType(IntEnum):
    ENABLE_MULTIPLAYER = 0
    DISABLE_MULTIPLAYER = 1
    REFRESH_JOINCODE = 2


@packet(id=139, since=388)
class MultiplayerSettingsPacket:
    packet_type: MultiplayerSettingsPacketType = field(type=uvarint32)


@packet(id=173, since=471)
class PhotoInfoRequestPacket:
    photo_id: varint64


@type(since=465)
class PhotoType(IntEnum):
    PORTFOLIO = 0
    PHOTO_ITEM = 1
    BOOK = 2


@packet(id=99)
class PhotoTransferPacket:
    """There is a camera item in EDU and they can use it to take screenshots and add them to a scrapbook."""

    photo_name: str
    photo_data: str
    book_id: str
    type: PhotoType = field(type=uint8, since=465)
    source_type: PhotoType = field(type=uint8, since=465)
    owner_id: int64 = field(since=465)
    new_photo_name: str = field(since=465)


@packet(id=324, since=786)
class PlayerVideoCapturePacket:
    """Used by a test command to start/stop video capture."""

    class StartVideoCapture:
        frame_rate: uint32
        file_prefix: str

    class StopVideoCapture:
        pass

    params: StartVideoCapture | StopVideoCapture


@packet(id=92)
class PurchaseReceiptPacket:
    """Sent from client to server."""

    purchase_receipts: list[str]


@packet(id=305, since=618)
class RefreshEntitlementsPacket:
    pass


class AbilitiesIndex(IntEnum):
    INVALID = -1
    BUILD = 0
    MINE = 1
    DOORS_AND_SWITCHES = 2
    OPEN_CONTAINERS = 3
    ATTACK_PLAYERS = 4
    ATTACK_MOBS = 5
    OPERATOR_COMMANDS = 6
    TELEPORT = 7
    INVULNERABLE = 8
    FLYING = 9
    MAY_FLY = 10
    INSTABUILD = 11
    LIGHTNING = 12
    FLY_SPEED = 13
    WALK_SPEED = 14
    MUTED = 15
    WORLD_BUILDER = 16
    NO_CLIP = 17
    PRIVILEGED_BUILDER = value(18, since=575)
    VERTICAL_FLY_SPEED = value(19, since=776)


@packet(id=184, since=527)
class RequestAbilityPacket:
    """Sent from client to server. Used to request an ability change."""

    class Type(IntEnum):
        UNSET = 0
        BOOL = 1
        FLOAT = 2

    ability: AbilitiesIndex = field(type=varint32)
    value_type: Type = field(type=uint8)
    bool_value: bool
    float_value: float


@packet(id=185, since=527)
class RequestPermissionsPacket:
    """Sent from client to server. Used to request a new Permissions Levels."""

    target_player_id: int64
    player_permissions: PlayerPermissionLevel = field(type=varint32)
    custom_permission_flags: uint16


@packet(id=347, since=975)
class ServerPresenceInfoPacket:
    """Sent by the server to provide PresenceConfiguration to the client."""

    presence_configuration: ServerConfiguration.PresenceConfiguration | None


@packet(id=102)
class ServerSettingsRequestPacket:
    """Sent during the initialization of world settings on the client."""


@packet(id=103)
class ServerSettingsResponsePacket:
    """Server Settings Response."""

    form_id: uvarint32
    form_json: str


@packet(id=192, since=554)
class ServerStatsPacket:
    """Used to send performance and other valuable stats back to the client."""

    server_time: float
    network_time: float


@packet(id=346, since=975)
class ServerStoreInfoPacket:
    """Sent by the server to provide ClientStoreEntryPointConfiguration to the client."""

    client_store_entry_point_configuration: ServerConfiguration.ClientStoreEntryPointConfiguration | None


@packet(id=105)
class SetDefaultGameTypePacket:
    """Same as SetPlayerGameTypePacket and UpdatePlayerGameTypePacket, the only difference is that this changes the
    default for all clients."""

    default_game_type: GameType = field(type=uvarint32)


@packet(id=60)
class SetDifficultyPacket:
    """Used for when a client changes difficulty through the menu or when the server changes the difficulty."""

    difficulty: Difficulty = field(type=uvarint32)


@packet(id=62)
class SetPlayerGameTypePacket:
    """The client handles the change of the UI element (the gametype dropdown,
    although this can be avoided by changing via command or on the server), then
    the client sends a packet to the server, then the server changes the player's
    gametype and sends a packet back (UpdatePlayerGameTypePacket) to make sure it
    matches on the client."""

    player_game_type: GameType = field(type=uvarint32)


@packet(id=10)
class SetTimePacket:
    """Every so often (and at login) the server sends the current time to the
    client, and additionally the client can set the server time through 2
    commands: DayLockCommand and TimeCommand."""

    time: varint32


@packet(id=75)
class ShowCreditsPacket:
    """That packet is sent to the client. When the credits have concluded, a
    packet is sent back to the server to let it know to reinstate the player
    watching the credits."""

    class CreditsState(IntEnum):
        START = 0
        FINISHED = 1

    player_id: ActorRuntimeID
    credits_state: CreditsState = field(type=varint32)


@packet(id=104)
class ShowProfilePacket:
    """The only use in vanilla is a test command called ProfileCommand. It makes
    the user's xbox profile popup."""

    player_xuid: str


class ShowStoreOfferRedirectTypeLegacy(IntEnum):
    """Legacy boolean carrier removed at v630 in favor of
    `ShowStoreOfferRedirectType`."""

    SHOW_TO_ALL = 0
    SHOWN_TO_OWNER = 1


class ShowStoreOfferRedirectType(IntEnum):
    MARKETPLACE_OFFER = 0
    DRESSING_ROOM_OFFER = 1
    THIRD_PARTY_SERVER_PAGE = 2


@packet(id=91)
class ShowStoreOfferPacket:
    """The server can redirect the user to a 3rd party server page, to a
    marketplace offer description page, or to a dressing room page containing
    desired offer."""

    offer_id: str = field(until=859)
    offer_id: uuid.UUID = field(since=859)
    shown_to_all: bool = field(until=630)
    redirect_type: ShowStoreOfferRedirectType = field(type=uint8, since=630)


@packet(id=64)
class SimpleEventPacket:
    """This is fired from the client to the server and a SetCommandsEnabledPacket
    is sent back when enabling commands."""

    class Subtype(IntEnum):
        UNINITIALIZED_SUBTYPE = 0
        ENABLE_COMMANDS = 1
        DISABLE_COMMANDS = 2
        UNLOCK_WORLD_TEMPLATE_SETTINGS = 3

    subtype: Subtype = field(type=uint16)


@type(since=448)
class SimulationType(IntEnum):
    GAME = 0
    EDITOR = 1
    TEST = 2
    INVALID = 3


@packet(id=168, since=448)
class SimulationTypePacket:
    sim_type: SimulationType = field(type=uint8)


@packet(id=11)
class StartGamePacket:
    entity_id: ActorUniqueID
    runtime_id: ActorRuntimeID
    entity_game_type: GameType = field(type=uvarint32)
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
    items: list[ItemEntry] = field(since=419, until=776)
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
    server_configuration_join_info: ServerConfigurationJoinInfo | None = field(since=924)
    server_telemetry_data: ServerTelemetryData = field(since=924)


class TimeMarkerData:
    id: uint64 = field(type=uvarint64)
    name: str
    time: int32 = field(type=varint32)
    period: int32 | None


class SyncWorldClockStateData:
    clock_id: uint64 = field(type=uvarint64)
    time: int32 = field(type=varint32)
    is_paused: bool


class WorldClockData:
    id: uint64 = field(type=uvarint64)
    name: str
    time: int32 = field(type=varint32)
    is_paused: bool
    time_markers: list[TimeMarkerData]


@packet(id=344, since=944)
class SyncWorldClocksPacket:
    """Initializes and syncs world clocks from the server to clients. (Currently disabled)"""

    class SyncStateData:
        clock_data: list[SyncWorldClockStateData]

    class InitializeRegistryData:
        clock_data: list[WorldClockData]

    class AddTimeMarkerData:
        clock_id: uint64 = field(type=uvarint64)
        time_markers: list[TimeMarkerData]

    class RemoveTimeMarkerData:
        clock_id: uint64 = field(type=uvarint64)
        time_marker_ids: list[uvarint64]

    data: (
        SyncStateData
        | InitializeRegistryData
        | AddTimeMarkerData
        | RemoveTimeMarkerData
    )


class TextPacketType(IntEnum):
    RAW = 0
    CHAT = 1
    TRANSLATE = 2
    POPUP = 3
    JUKEBOX_POPUP = 4
    TIP = 5
    SYSTEM_MESSAGE = 6
    WHISPER = 7
    ANNOUNCEMENT = 8
    TEXT_OBJECT_WHISPER = value(9, since=332)
    TEXT_OBJECT = value(10, since=554)
    TEXT_OBJECT_ANNOUNCEMENT = value(11, since=554)


@packet(id=9)
class TextPacket:
    """Represents a text message that needs to be displayed in-game. Used for commands, messages, and other info
    printed to the screen. Most of which are server->client or server broadcasted to all clients, but some cases have
    a client to other client via the server."""

    localize: bool
    # COMPILER_EXTENSION_NEEDED: the variant body's three cases differ structurally
    # (message_type+message / message_type+player_name+message / message_type+message+list[str])
    # and share no leading uvarint32 case-tag in pre-v898 wire shapes
    message_type: TextPacketType = field(type=uint8)
    xuid: str
    platform_id: str
    filtered_message: str | None = field(since=685)


# TickSyncPacket (id=23, v388..v685) is omitted: removed before v975 and the
# DSL cannot express a lone @packet(until=) today.


@packet(id=179, since=503)
class TickingAreasLoadStatusPacket:
    """Used to inform the client that the server is waiting for ticking areas to finish preloading."""

    waiting_for_preload: bool


@packet(id=85)
class TransferPacket:
    """Used to kick off transferring the client between online games, or it can be used to cause players to quit the
    world and rejoin."""

    destination: str
    destination_port: uint16
    reload_world: bool = field(since=729)


class UpdateAbilitiesSerializedLayer:
    serialized_layer: uint16
    abilities_set: uint32
    ability_values: uint32
    fly_speed: float
    vertical_fly_speed: float = field(since=776)
    walk_speed: float


class UpdateAbilitiesSerializedData:
    target_player: ActorUniqueID = field(type=int64)
    player_permissions: PlayerPermissionLevel = field(type=uint8)
    command_permissions: CommandPermissionLevel = field(type=uint8)
    layers: list[UpdateAbilitiesSerializedLayer]


@packet(id=187, since=534)
class UpdateAbilitiesPacket:
    """Sent by the server to update the state of a player's Abilities."""

    data: UpdateAbilitiesSerializedData


class AdventureSettings:
    no_pv_m: bool
    no_mv_p: bool
    immutable_world: bool
    show_name_tags: bool
    auto_jump: bool


@packet(id=188, since=534)
class UpdateAdventureSettingsPacket:
    """Sent by the server to update the state of AdventureSettings. Replaces the
    AdventureSettingsPacket for updating AdventureSettings from server to
    client."""

    adventure_settings: AdventureSettings


@packet(id=151, since=407)
class UpdatePlayerGameTypePacket:
    """The server will send this back to all clients on receipt of the SetPlayerGameTypePacket so that cached game type
    and permissions flags in mLevel on all clients is kept up to date."""

    player_game_type: GameType = field(type=uvarint32)
    target_player: ActorUniqueID
    tick: PlayerInputTick = field(since=671)


# VideoStreamConnectPacket (id=125, v340..v361) is omitted: removed before v975
# and the DSL cannot express a lone @packet(until=) today.


class SerializableCells:
    x_size: uint8
    y_size: uint8
    z_size: uint8
    storage: list[uint8]


class SerializableVoxelShape:
    cells: SerializableCells
    x_coords: list[float]
    y_coords: list[float]
    z_coords: list[float]


@packet(id=337, since=924)
class VoxelShapesPacket:
    """Sends the serializable voxel shapes data to the client as it's needed on both the client and server. This packet
    should always be sent before StartGamePacket."""

    shapes: list[SerializableVoxelShape]
    name_map: dict[str, uint16] = field(prefix=uvarint32)
    custom_shape_count: uint16 = field(since=944)
