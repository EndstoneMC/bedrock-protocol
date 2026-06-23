import uuid
from enum import IntEnum, IntFlag

from protocol import (
    bitset,
    field,
    int8,
    int16,
    int32,
    int64,
    packet,
    uint8,
    uint16,
    uint32,
    uvarint32,
    uvarint64,
    value,
    varint32,
    varint64,
)
from protocol.common import BlockPos, NetworkBlockPos, Vec2, Vec3
from protocol.dimension import DimensionType
from protocol.game import GameType
from protocol.inventory import NetworkItemStackDescriptor
from protocol.molang import MolangVersion
from protocol.nbt import CompoundTag

package = "bedrock.protocol"

type ActorRuntimeID = uvarint64
type ActorUniqueID = varint64


class ActorEvent(IntEnum):
    NONE = 0
    JUMP = 1
    HURT = 2
    DEATH = 3
    START_ATTACKING = 4
    STOP_ATTACKING = 5
    TAMING_FAILED = 6
    TAMING_SUCCEEDED = 7
    SHAKE_WETNESS = 8
    EAT_GRASS = 10
    FISHHOOK_BUBBLE = 11
    FISHHOOK_FISHPOS = 12
    FISHHOOK_HOOKTIME = 13
    FISHHOOK_TEASE = 14
    SQUID_FLEEING = 15
    ZOMBIE_CONVERTING = 16
    PLAY_AMBIENT = 17
    SPAWN_ALIVE = 18
    START_OFFER_FLOWER = 19
    STOP_OFFER_FLOWER = 20
    LOVE_HEARTS = 21
    VILLAGER_ANGRY = 22
    VILLAGER_HAPPY = 23
    WITCH_HAT_MAGIC = 24
    FIREWORKS_EXPLODE = 25
    IN_LOVE_HEARTS = 26
    SILVERFISH_MERGE_ANIM = 27
    GUARDIAN_ATTACK_SOUND = 28
    DRINK_POTION = 29
    THROW_POTION = 30
    PRIME_TNTCART = 31
    PRIME_CREEPER = 32
    AIR_SUPPLY = 33
    DEPRECATED_ADD_PLAYER_LEVELS = 34
    GUARDIAN_MINING_FATIGUE = 35
    AGENT_SWING_ARM = 36
    DRAGON_START_DEATH_ANIM = 37
    GROUND_DUST = 38
    SHAKE = 39
    FEED = 57
    BABY_AGE = 60
    INSTANT_DEATH = 61
    NOTIFY_TRADE = 62
    LEASH_DESTROYED = 63
    CARAVAN_UPDATED = 64
    TALISMAN_ACTIVATE = 65
    DEPRECATED_UPDATE_STRUCTURE_FEATURE = 66
    PLAYER_SPAWNED_MOB = 67
    PUKE = 68
    UPDATE_STACK_SIZE = 69
    START_SWIMMING = 70
    BALLOON_POP = 71
    TREASURE_HUNT = 72
    SUMMON_AGENT = 73
    FINISHED_CHARGING_ITEM = 74
    LANDED_ON_GROUND = value(75, until=622)
    ACTOR_GROW_UP = 76
    VIBRATION_DETECTED = 77
    DRINK_MILK = 78
    SHAKE_WETNESS_STOP = value(79, since=859)
    KINETIC_DAMAGE_DEALT = value(80, since=897)
    HURT_WITHOUT_RECEIVING_DAMAGE = value(81, since=975)


class MoveActorAbsoluteData:
    class Header(IntFlag):
        IS_ON_GROUND = 1 << 0
        FORCE_MOVE = 1 << 1
        FORCE_MOVE_LOCAL_ENTITY = 1 << 2
        FORCE_COMPLETION = 1 << 3

    runtime_id: ActorRuntimeID
    header: Header = field(type=uint8)
    position: Vec3
    rotation_x: uint8
    rotation_y: uint8
    rotation_y_head: uint8


@packet(id=18)
class MoveActorAbsolutePacket:
    move_data: MoveActorAbsoluteData


@packet(id=27)
class ActorEventPacket:
    """All kinds of actor state changes (see Actor::handleEntityEvent). Ranges from
    a crossbow being ready to fire to taming animals, some of which may be obsolete
    (frex, ADD_PLAYER_LEVELS)."""

    runtime_id: ActorRuntimeID
    event_id: ActorEvent = field(type=uint8)
    data: varint32
    fire_at_position: Vec3 | None = field(since=975)


class ActorSwingSource(IntEnum):
    NONE = 0
    BUILD = 1
    MINE = 2
    INTERACT = 3
    ATTACK = 4
    USE_ITEM = 5
    THROW_ITEM = 6
    DROP_ITEM = 7
    EVENT = 8


@packet(id=44)
class AnimatePacket:
    """Combination of server bound and client bound packets to trigger animations."""

    class Action(IntEnum):
        NO_ACTION = 0
        SWING = 1
        WAKE_UP = 3
        CRITICAL_HIT = 4
        MAGIC_CRITICAL_HIT = 5
        ROW_RIGHT = value(128, until=897)
        ROW_LEFT = value(129, until=897)

    action: Action = field(type=varint32, until=897)
    action: Action = field(type=uint8, since=897)
    runtime_id: ActorRuntimeID
    data: float = field(since=859)
    swing_source: ActorSwingSource | None = field(type=str, since=897)
    rowing_time: float = field(
        when=lambda p: p.action == Action.ROW_LEFT or p.action == Action.ROW_RIGHT,
        until=897,
    )


@packet(id=158, since=419)
class AnimateEntityPacket:
    """The AnimateEntityPacket is used to trigger a one-off animation on the client
    it is sent to."""

    animation: str
    next_state: str
    stop_expression: str
    stop_expression_version: MolangVersion = field(type=int32, since=465)
    controller: str
    blend_out_time: float
    runtime_ids: list[ActorRuntimeID]


@packet(id=152, since=407)
class EmoteListPacket:
    """Allows clients to download emotes that other clients have equipped."""

    runtime_id: ActorRuntimeID
    emote_piece_ids: list[uuid.UUID]


@packet(id=33)
class InteractPacket:
    """Used for inventory button press and in _updateInteraction() for a variety of
    purposes. From the client."""

    class Action(IntEnum):
        INVALID = 0
        STOP_RIDING = 3
        INTERACT_UPDATE = 4
        NPC_OPEN = 5
        OPEN_INVENTORY = 6

    action: Action = field(type=uint8)
    target_id: ActorRuntimeID
    pos: Vec3 = field(when=lambda p: p.action == Action.INTERACT_UPDATE, until=388)
    pos: Vec3 = field(
        when=lambda p: p.action == Action.INTERACT_UPDATE or p.action == Action.STOP_RIDING,
        since=388,
        until=897,
    )
    pos: Vec3 | None = field(since=897)


@packet(id=119, since=313)
class AvailableActorIdentifiersPacket:
    """Sends the whole list of actor identifiers at game start from the server."""

    identifier_list: CompoundTag


@packet(id=89)
class AddBehaviorTreePacket:
    json_input: str


class ActorLinkType(IntEnum):
    NONE = 0
    RIDING = 1
    PASSENGER = 2


class ActorLink:
    from_actor_id: ActorUniqueID
    to_actor_id: ActorUniqueID
    type: ActorLinkType = field(type=uint8)
    immediate: bool
    passenger_initiated: bool = field(since=407)
    vehicle_angular_velocity: float = field(since=712)


class PropertySyncData:
    class PropertySyncIntEntry:
        property_index: uvarint32
        data: varint32

    class PropertySyncFloatEntry:
        property_index: uvarint32
        data: float

    int_entries: "list[PropertySyncIntEntry]"
    float_entries: "list[PropertySyncFloatEntry]"


class SyncedAttribute:
    name: str
    min_value: float
    current_value: float
    max_value: float


class DataItem:
    class Type(IntEnum):
        BYTE = 0
        SHORT = 1
        INT = 2
        FLOAT = 3
        STRING = 4
        COMPOUND_TAG = 5
        POS = 6
        INT64 = 7
        VEC3 = 8

    id: uvarint32
    value: uint8 | int16 | varint32 | float | str | CompoundTag | BlockPos | varint64 | Vec3 = field(
        tag=Type, type=uvarint32
    )


@packet(id=13)
class AddActorPacket:
    entity_id: ActorUniqueID
    runtime_id: ActorRuntimeID
    actor_type: uvarint32 = field(until=313)
    actor_type: str = field(since=313)
    pos: Vec3
    velocity: Vec3
    rot: Vec2
    y_head_rotation: float
    y_body_rotation: float = field(since=534)
    attributes: list[SyncedAttribute]
    packed_items: list[DataItem]
    synched_properties: PropertySyncData = field(since=557)
    links: list[ActorLink]


@packet(id=16, until=361)
class AddHangingEntityPacket:
    actor_id: ActorUniqueID
    runtime_id: ActorRuntimeID
    position: NetworkBlockPos
    direction: varint32


@packet(id=15)
class AddItemActorPacket:
    """Makes an item entity show up. One of the few entities that cannot be sent via AddActorPacket."""

    entity_id: ActorUniqueID
    runtime_id: ActorRuntimeID
    item: NetworkItemStackDescriptor
    pos: Vec3
    velocity: Vec3
    packed_items: list[DataItem]
    from_fishing: bool


@packet(id=22)
class AddPaintingPacket:
    """Sends the information for a new painting actor from server to client."""

    entity_id: ActorUniqueID
    runtime_id: ActorRuntimeID
    pos: NetworkBlockPos = field(until=361)
    pos: Vec3 = field(since=361)
    dir: varint32
    motif: str


class BuildPlatform(IntEnum):
    UNKNOWN = -1
    GOOGLE = 1
    IOS = 2
    OSX = 3
    AMAZON = 4
    GEAR_VR = 5
    UWP = 7
    WIN32 = 8
    DEDICATED = 9
    TV_OS = 10
    SONY = 11
    NX = 12
    XBOX = 13
    WINDOWS_PHONE = 14
    LINUX = 15


# PlayerPermissionLevel lives in protocol.game. We cannot import it without a
# circular dependency (game imports ActorRuntimeID from here). Wire form is
# uint8 for SerializedAbilitiesData; emit as raw uint8.


class CommandPermissionLevel(IntEnum):
    ANY = 0
    GAME_DIRECTORS = 1
    ADMIN = 2
    HOST = 3
    OWNER = 4
    INTERNAL = 5


class AbilitiesLayer(IntEnum):
    CUSTOM_CACHE = 0
    BASE = 1
    SPECTATOR = 2
    COMMANDS = 3
    EDITOR = 4
    LOADING_SCREEN = value(5, since=712)


class SerializedLayer:
    serialized_layer: AbilitiesLayer = field(type=uint16)
    abilities_set: uint32
    ability_values: uint32
    fly_speed: float
    vertical_fly_speed: float = field(since=776)
    walk_speed: float


class SerializedAbilitiesData:
    target_player: ActorUniqueID = field(type=int64)
    # PlayerPermissionLevel lives in protocol.game (circular import); writing as
    # raw uint8 of the enum value.
    player_permissions: uint8
    command_permissions: CommandPermissionLevel = field(type=uint8)
    layers: list[SerializedLayer]


class AdventureSettingsBody:  # pre-v534 wire shape, pre-v776 BDS-invisible; trust CloudburstMC
    flags1: int32 = field(type=varint32)
    command_permission: CommandPermissionLevel = field(type=varint32)
    flags2: int32 = field(type=varint32)
    # PlayerPermissionLevel lives in protocol.game (circular import); writing as
    # raw varint32 of the enum value.
    player_permission: varint32
    custom_flags: int32 = field(type=varint32)
    entity_unique_id: int64


@packet(id=12)
class AddPlayerPacket:
    """Makes a player entity show up client-side. One of the few entities that cannot be sent via AddActorPacket."""

    uuid: uuid.UUID
    username: str
    entity_id: ActorUniqueID = field(until=534)
    runtime_id: ActorRuntimeID
    platform_chat_id: str
    position: Vec3
    velocity: Vec3
    pitch: float
    yaw: float
    head_yaw: float
    held_item: NetworkItemStackDescriptor
    game_type: GameType = field(type=varint32, since=503)
    packed_items: list[DataItem]
    properties: PropertySyncData = field(since=557)
    adventure_settings: AdventureSettingsBody = field(until=534)
    abilities: SerializedAbilitiesData = field(since=534)
    links: list[ActorLink]
    device_id: str
    build_platform: BuildPlatform = field(type=int32, since=388)


@packet(id=166, since=440)
class AddVolumeEntityPacket:
    """Sends a volume entity's definition and components from server to client."""

    entity_net_id: uvarint32
    components: CompoundTag
    json_identifier: str = field(since=486)
    instance_name: str = field(since=486)
    min_bounds: NetworkBlockPos = field(since=503, until=944)
    min_bounds: BlockPos = field(since=944)
    max_bounds: NetworkBlockPos = field(since=503, until=944)
    max_bounds: BlockPos = field(since=944)
    dimension_type: DimensionType = field(since=503)
    min_engine_version: str = field(since=465)


class BossEventUpdateType(IntEnum):
    ADD = 0
    PLAYER_ADDED = 1
    REMOVE = 2
    PLAYER_REMOVED = 3
    UPDATE_PERCENT = 4
    UPDATE_NAME = 5
    UPDATE_PROPERTIES = 6
    UPDATE_STYLE = 7
    QUERY = value(8, since=486)


class BossBarColor(IntEnum):
    PINK = 0
    BLUE = 1
    RED = 2
    GREEN = 3
    YELLOW = 4
    PURPLE = 5
    REBECCA_PURPLE = 6
    WHITE = 7


class BossBarOverlay(IntEnum):
    PROGRESS = 0
    NOTCHED_6 = 1
    NOTCHED_10 = 2
    NOTCHED_12 = 3
    NOTCHED_20 = 4


@packet(id=74, until=1001)
class BossEventPacket:
    """Sent when a boss gets updated"""

    boss_id: ActorUniqueID
    event_type: BossEventUpdateType = field(type=uvarint32)

    # player_id is also written for QUERY from 486 on; QUERY (value 8) does not
    # exist before 486, so this single condition is exact across all versions
    # (a version-redeclaration here is disallowed once the packet itself is one).
    player_id: ActorUniqueID = field(
        when=lambda p: (
            p.event_type
            in {BossEventUpdateType.PLAYER_ADDED, BossEventUpdateType.PLAYER_REMOVED, BossEventUpdateType.QUERY}
        ),
    )

    # Pre-776: a single `name` field gated on ADD or UPDATE_NAME. From 776 BDS
    # adds a parallel `filtered_name` next to it. Modelling only the v776+ form
    # here -- the pre-776 redeclaration would overlap with the with-block, which
    # the DSL does not currently support for nested field redeclarations.
    with field(
        when=lambda p: p.event_type in {BossEventUpdateType.ADD, BossEventUpdateType.UPDATE_NAME},
        since=776,
    ):
        name: str
        filtered_name: str

    health_percent: float = field(
        when=lambda p: p.event_type in {BossEventUpdateType.ADD, BossEventUpdateType.UPDATE_PERCENT},
    )
    darken_screen: uint16 = field(
        when=lambda p: p.event_type in {BossEventUpdateType.ADD, BossEventUpdateType.UPDATE_PROPERTIES},
    )

    with field(
        when=lambda p: (
            p.event_type
            in {BossEventUpdateType.ADD, BossEventUpdateType.UPDATE_PROPERTIES, BossEventUpdateType.UPDATE_STYLE}
        )
    ):
        color: BossBarColor = field(type=uvarint32)
        overlay: BossBarOverlay = field(type=uvarint32)


# v1001 (cereal migration): flat layout, every field always written,
# darken_screen dropped. event_type / color / overlay stay uvarint32 -- the
# small-enum byte-aliasing makes the reference libraries' uint8 indistinguishable
# from the cereal uvarint32 (all values fit in one byte either way).
@packet(id=74, since=1001)
class BossEventPacket:
    """Sent when a boss gets updated"""

    boss_id: ActorUniqueID
    player_id: ActorUniqueID
    event_type: BossEventUpdateType = field(type=uvarint32)
    name: str
    filtered_name: str
    health_percent: float
    color: BossBarColor = field(type=uvarint32)
    overlay: BossBarOverlay = field(type=uvarint32)


@packet(id=182, since=503)
class ChangeMobPropertyPacket:
    """packet containing data for changing mob property"""

    actor_id: ActorUniqueID
    prop_name: str
    bool_component_val: bool
    string_component_val: str
    int_component_val: varint32
    float_component_val: float


class ItemUseMethod(IntEnum):
    UNKNOWN = -1
    EQUIP_ARMOR = 0
    EAT = 1
    ATTACK = 2
    CONSUME = 3
    THROW = 4
    SHOOT = 5
    PLACE = 6
    FILL_BOTTLE = 7
    FILL_BUCKET = 8
    POUR_BUCKET = 9
    USE_TOOL = 10
    INTERACT = 11
    RETRIEVED = 12
    DYED = 13
    TRADED = 14
    BRUSHING_COMPLETED = 15
    OPENED_VAULT = 16


@packet(id=142, since=388)
class CompletedUsingItemPacket:
    """Send server to client to complete the using item process. An example is when you finish drinking or eating."""

    item_id: int16
    item_use_method: ItemUseMethod = field(type=int32)


@packet(id=138, since=388)
class EmotePacket:
    """A client sends this to the server to notify other clients about the emote."""

    class Flags(IntEnum):
        SERVER_SIDE = 1
        MUTE_EMOTE_CHAT = 2

    runtime_id: ActorRuntimeID
    piece_id: str
    emote_ticks: uvarint32 = field(since=729)
    xuid: str = field(since=589)
    platform_id: str = field(since=589)
    flags: Flags = field(type=uint8)


@packet(id=37)
class ActorFallPacket:
    runtime_id: ActorRuntimeID
    fall_distance: float
    in_void: bool


@packet(id=35)
class ActorPickRequestPacket:
    """Player clicks on an actor in the world, eg a chicken."""

    # Wire: little-endian int64, not the usual varint actor id.
    id: int64
    max_slots: uint8
    with_data: bool = field(since=465)


# ActorDamageCause is a large enum; wire is a varint of the underlying int.
type ActorDamageCause = varint32


@packet(id=38)
class HurtArmorPacket:
    """Sends the damage taken after armor is taken into account. This looks like it is trying
    to be phased out, this is not sent while the ItemStackNetManagerServer is active. From the
    server."""

    cause: ActorDamageCause = field(since=407)
    dmg: varint32
    # std::bitset<5>; BDS aliases as ArmorBitset.
    armor_slots: bitset[5] = field(since=465)


@packet(id=32)
class MobArmorEquipmentPacket:
    """Updates the armour an entity is wearing. Sent for players and other entities."""

    runtime_id: ActorRuntimeID
    helmet: NetworkItemStackDescriptor
    chestplate: NetworkItemStackDescriptor
    leggings: NetworkItemStackDescriptor
    boots: NetworkItemStackDescriptor
    body: NetworkItemStackDescriptor = field(since=712)


@packet(id=157, since=419)
class MotionPredictionHintsPacket:
    """It is essentially a SetActionMotionPacket with a bool indicating if the actor was on the
    ground at the time the packet is sent or not."""

    runtime_id: ActorRuntimeID
    motion: Vec3
    on_ground: bool


# MoveActorDeltaPacket header-bit predicate works in C++ only if `flags & enum`
# compiles, which `enum class` does not. The header bits live as plain integer
# constants on the wire and the BDS code masks them with raw uint16 values, so
# we mirror that by dropping the enum and using integer literals directly.
@packet(id=111)
class MoveActorDeltaPacket:
    # Header bits (mirror BDS MoveActorDeltaPacket::Flags):
    # HAS_POSITION_X = 1, HAS_POSITION_Y = 2, HAS_POSITION_Z = 4,
    # HAS_ROTATION_X = 8, HAS_ROTATION_Y = 16, HAS_ROTATION_Y_HEAD = 32,
    # IS_ON_GROUND = 64, FORCE_MOVE = 128, FORCE_MOVE_LOCAL_ENTITY = 256,
    # FORCE_COMPLETION = 512.
    runtime_id: ActorRuntimeID
    flags: uint8 = field(until=388)
    flags: uint16 = field(since=388)
    # v291..v418 wrote positional deltas as varint32, then v419 switched to absolute floats.
    new_position_x: varint32 = field(when=lambda p: p.flags & 1 != 0, until=419)
    new_position_x: float = field(when=lambda p: p.flags & 1 != 0, since=419)
    new_position_y: varint32 = field(when=lambda p: p.flags & 2 != 0, until=419)
    new_position_y: float = field(when=lambda p: p.flags & 2 != 0, since=419)
    new_position_z: varint32 = field(when=lambda p: p.flags & 4 != 0, until=419)
    new_position_z: float = field(when=lambda p: p.flags & 4 != 0, since=419)
    rot_x: int8 = field(when=lambda p: p.flags & 8 != 0)
    rot_y: int8 = field(when=lambda p: p.flags & 16 != 0)
    rot_y_head: int8 = field(when=lambda p: p.flags & 32 != 0)


@packet(id=14)
class RemoveActorPacket:
    """Occasionally, during the server player tick some time is taken to remove nearby actors from the world."""

    entity_id: ActorUniqueID


type EntityNetId = uvarint32


@packet(id=167, since=440)
class RemoveVolumeEntityPacket:
    """Sends a volume entity to be removed from server to client."""

    entity_net_id: EntityNetId
    dimension_type: DimensionType = field(since=503)


# PassengerJumpPacket (id=20, until=800) was removed at v800. The DSL requires
# a packet redeclaration to use until=, but no shape exists for v975. Drop the
# version gate -- the packet lives in the generated surface but BDS no longer
# uses it.
@packet(id=20)
class PassengerJumpPacket:
    jump_scale: uvarint32


@packet(id=39)
class SetActorDataPacket:
    runtime_id: ActorRuntimeID
    packed_items: list[DataItem]
    synched_properties: PropertySyncData = field(since=557)
    tick: uvarint64 = field(since=419)


@packet(id=41)
class SetActorLinkPacket:
    """Sent by both client and server, only received by LegacyClientHandler."""

    link: ActorLink


@packet(id=40)
class SetActorMotionPacket:
    """This is used for the server to set the velocity of a client actor."""

    runtime_id: ActorRuntimeID
    motion: Vec3
    tick: uvarint64 = field(since=662)


@packet(id=96)
class SetLastHurtByPacket:
    """Any time a player is hit, the id of the last mob that attacked them is sent to the client."""

    # TODO: protocol-docs reports the wire as uvarint32 (unsigned); gophertunnel and
    # CloudburstMC v291 both encode it as varint32 (signed). Reconcile against BDS.
    last_hurt_by: varint32


@packet(id=66)
class SpawnExperienceOrbPacket:
    pos: Vec3
    xp_value: varint32


@packet(id=165, since=440)
class SyncActorPropertyPacket:
    property_data: CompoundTag


@packet(id=17)
class TakeItemActorPacket:
    """From this the item and count is turned into an item and the transaction is handled afterwards."""

    item_id: ActorRuntimeID
    actor_id: ActorRuntimeID


@packet(id=306, since=630)
class PlayerToggleCrafterSlotRequestPacket:
    pos_x: int32
    pos_y: int32
    pos_z: int32
    slot_index: uint8
    is_disabled: bool


# ContainerID lives in protocol.inventory (signed-char in BDS,
# SharedTypes::Legacy::ContainerID). protocol.inventory imports protocol.actor,
# so we cannot import inventory here without a resolver cycle. Encode as raw
# int8 directly.


@packet(id=81)
class UpdateEquipPacket:
    """Seemingly only used for the Horse Inventory. More specifically when the player opens the horse inventory."""

    container_id: int8
    type: int8
    size: varint32
    entity_unique_id: ActorUniqueID
    data: CompoundTag


@packet(id=80)
class UpdateTradePacket:
    """This is used when the player trades with an npc. This sends all of the updated trade info
    in one big ol' packet."""

    container_id: int8
    type: int8
    size: varint32
    # v291 wrote a merchant-timer varint here (40 when economy trading), v313
    # wrote it (40 when new-trading-ui) and added trader_tier next. v354 dropped
    # the legacy timer and moved use_new_trade_screen / using_economy_trade
    # after display_name. The booleans live on the wire only from v354.
    merchant_timer: varint32 = field(until=354)
    trader_tier: varint32 = field(since=313)
    recipe_added_on_update: bool = field(until=354)
    entity_unique_id: ActorUniqueID
    last_trading_player: ActorUniqueID
    display_name: str
    use_new_trade_screen: bool = field(since=354)
    using_economy_trade: bool = field(since=354)
    data: CompoundTag
