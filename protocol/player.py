"""The player as a subject: world/actor/player/ -- respawn state, damage cause,
armour slots, client options, the player list, per-player location and property overrides,
and AddPlayer. Not abilities -- those are in ability.py."""

import uuid
from enum import Enum, IntEnum, auto

from protocol import field, int16, int32, packet, type, uint8, uvarint32, uvarint64, value, varint32
from protocol.ability import SerializedAbilitiesData
from protocol.actor import ActorLink, ActorRuntimeID, ActorUniqueID, PropertySyncData, SynchedActorData
from protocol.common import BlockPos, Color, DimensionType, Vec2, Vec3
from protocol.game import GameType
from protocol.item import NetworkItemStackDescriptor, SerializedNetworkItemStackDescriptor
from protocol.skin import SerializedSkinRef

package = "bedrock.protocol"


class PlayerRespawnState(IntEnum, uint8):
    SEARCHING_FOR_SPAWN = 0
    READY_TO_SPAWN = 1
    CLIENT_READY_TO_SPAWN = 2


@packet(id=45)
class RespawnPacket:
    pos: Vec3
    state: PlayerRespawnState
    runtime_id: ActorRuntimeID


class ActorDamageCause(IntEnum):
    NONE = -1
    OVERRIDE = 0
    CONTACT = 1
    ENTITY_ATTACK = 2
    PROJECTILE = 3
    SUFFOCATION = 4
    FALL = 5
    FIRE = 6
    FIRE_TICK = 7
    LAVA = 8
    DROWNING = 9
    BLOCK_EXPLOSION = 10
    ENTITY_EXPLOSION = 11
    VOID = 12
    SELF_DESTRUCT = 13
    MAGIC = 14
    WITHER = 15
    STARVE = 16
    ANVIL = 17
    THORNS = 18
    FALLING_BLOCK = 19
    PISTON = 20
    FLY_INTO_WALL = 21
    MAGMA = 22
    FIREWORKS = 23
    LIGHTNING = 24
    CHARGING = 25
    TEMPERATURE = 26
    FREEZING = 27
    STALACTITE = 28
    STALAGMITE = 29
    RAM_ATTACK = 30
    SONIC_BOOM = 31
    CAMPFIRE = 32
    SOUL_CAMPFIRE = 33
    MACE_SMASH = 34
    ALL = 35


@packet(id=38)
class HurtArmorPacket:
    cause: ActorDamageCause
    dmg: varint32
    armor_slots: uvarint64


@packet(id=42)
class SetHealthPacket:
    health: varint32


@packet(id=309)
class AwardAchievementPacket:
    achievement_id: int32


@packet(id=33)
class InteractPacket:
    class Action(IntEnum, uint8):
        INVALID = 0
        STOP_RIDING = 3
        INTERACT_UPDATE = 4
        NPC_OPEN = 5
        OPEN_INVENTORY = 6

    action: Action
    target_id: ActorRuntimeID
    pos: Vec3 | None


class SpawnPositionType(IntEnum):
    PLAYER_RESPAWN = 0
    WORLD_SPAWN = 1


@packet(id=43)
class SetSpawnPositionPacket:
    spawn_pos_type: SpawnPositionType
    pos: BlockPos
    dimension_type: DimensionType
    spawn_block_pos: BlockPos


@packet(id=113)
class SetLocalPlayerAsInitializedPacket:
    player_id: ActorRuntimeID


class ArmorSlot(IntEnum):
    HEAD = 0
    TORSO = 1
    LEGS = 2
    FEET = 3
    BODY = 4
    HUMANOID_COUNT = 4
    COUNT = auto()


class ArmorSlotAndDamagePair:
    armor_slot: ArmorSlot
    damage: int16


@packet(id=149)
class PlayerArmorDamagePacket:
    slot_and_damage_pairs: list[ArmorSlotAndDamagePair]


@packet(id=160)
class PlayerFogPacket:
    fog_stack: list[str]


class GraphicsMode(IntEnum, uint8):
    SIMPLE = 0
    FANCY = 1
    ADVANCED = 2
    RAY_TRACED = 3


@packet(id=323)
class UpdateClientOptionsPacket:
    graphics_mode: GraphicsMode | None
    filter_profanity: bool | None


class PlayerListPacketType(IntEnum, uint8):
    ADD = 0
    REMOVE = 1


class BuildPlatform(IntEnum):
    UNKNOWN = -1
    GOOGLE = 1
    IOS = value(2, cpp_name="IOS")
    OSX = value(3, cpp_name="OSX")
    AMAZON = 4
    GEAR_VR_DEPRECATED = value(5, cpp_name="GearVRDeprecated")
    UWP_DEPRECATED = value(7, cpp_name="UWPDeprecated")
    WIN32 = 8
    DEDICATED = 9
    TV_OS_DEPRECATED = value(10, cpp_name="TvOSDeprecated")
    SONY = 11
    NINTENDO = 12
    XBOX = 13
    WINDOWS_PHONE_DEPRECATED = 14
    LINUX = 15


@type(until=2168)
class PlayerListEntry:
    uuid: uuid.UUID
    id: ActorUniqueID
    name: str
    xuid: str
    platform_online_id: str
    build_platform: BuildPlatform = field(type=int32)
    skin: SerializedSkinRef = field(cereal=False)
    is_teacher: bool
    is_host: bool
    is_sub_client: bool
    color: Color


@packet(id=63, until=2168)
class PlayerListPacket:
    action: PlayerListPacketType
    entries: list[PlayerListEntry] = field(when=lambda p: p.action == PlayerListPacketType.ADD)
    removed_entries: list[uuid.UUID] = field(when=lambda p: p.action == PlayerListPacketType.REMOVE)
    trusted_skins: list[bool] = field(
        when=lambda p: p.action == PlayerListPacketType.ADD,
        count=lambda p: len(p.entries),
    )


@packet(id=63, since=2168)
class PlayerListPacket:
    """Each entry carries its action twice: once as the variant index over the two
    payloads, then again as the payload's own member."""

    class RemoveEntry:
        action: PlayerListPacketType
        uuid: uuid.UUID

    class AddEntry:
        action: PlayerListPacketType
        uuid: uuid.UUID
        id: ActorUniqueID
        name: str
        xuid: str
        platform_online_id: str
        build_platform: BuildPlatform = field(type=int32)
        skin: SerializedSkinRef
        is_teacher: bool
        is_host: bool
        is_sub_client: bool
        color: Color

    entries: list[RemoveEntry | AddEntry]


class UpdateType(Enum, uint8):
    CLEAR_OVERRIDES = 0
    REMOVE_OVERRIDE = 1
    SET_INT_OVERRIDE = 2
    SET_FLOAT_OVERRIDE = 3


@packet(id=325, until=2168)
class PlayerUpdateEntityOverridesPacket:
    id: ActorUniqueID
    property_index: uvarint32
    update_type: UpdateType
    int_value: int32 = field(when=lambda p: p.update_type == UpdateType.SET_INT_OVERRIDE)
    float_value: float = field(when=lambda p: p.update_type == UpdateType.SET_FLOAT_OVERRIDE)


@packet(id=325, since=2168)
class PlayerUpdateEntityOverridesPacket:
    # TODO: confirm against BDS -- PlayerUpdateEntityOverridesPacket.h gives these payloads no
    # tag member at all (ClearOverride and RemoveOverride are empty structs and the type comes
    # from getUpdateType()), so the header settles nothing beyond UpdateType being uint8_t. The
    # r26_u4 dump name-codes the tag inside each payload while typing the variant's own switch
    # uint8; CloudburstMC PlayerUpdateEntityOverridesSerializer_v2168 writes a single byte.
    # Needs cerealizer<PlayerUpdateEntityOverridesPacketPayload>::bind read directly.
    class ClearOverride:
        update_type: UpdateType = field(type=str)

    class RemoveOverride:
        update_type: UpdateType = field(type=str)

    class IntOverride:
        update_type: UpdateType = field(type=str)
        value: int32

    class FloatOverride:
        update_type: UpdateType = field(type=str)
        value: float

    id: ActorUniqueID
    property_index: uvarint32
    update: ClearOverride | RemoveOverride | IntOverride | FloatOverride


@packet(id=326, until=2168)
class PlayerLocationPacket:
    class Type(IntEnum):
        PLAYER_LOCATION_COORDINATES = 0
        PLAYER_LOCATION_HIDE = 1

    type: Type = field(type=int32)
    id: ActorUniqueID
    pos: Vec3 = field(when=lambda p: p.type == Type.PLAYER_LOCATION_COORDINATES)


@packet(id=326, since=2168)
class PlayerLocationPacket:
    class Type(IntEnum):
        PLAYER_LOCATION_COORDINATES = 0
        PLAYER_LOCATION_HIDE = 1

    class CoordinatesLocation:
        type: Type
        pos: Vec3

    class HiddenLocation:
        type: Type

    id: ActorUniqueID
    location: CoordinatesLocation | HiddenLocation


@packet(id=12, until=2168)
class AddPlayerPacket:
    uuid: uuid.UUID
    name: str
    runtime_id: ActorRuntimeID
    platform_online_id: str
    pos: Vec3
    velocity: Vec3
    rot: Vec2
    y_head_rot: float
    carried_item: NetworkItemStackDescriptor
    player_game_type: GameType
    unpack: SynchedActorData.CopyableDataList
    synched_properties: PropertySyncData
    abilities_data: SerializedAbilitiesData
    links: list[ActorLink]
    device_id: str
    build_platform: BuildPlatform = field(type=int32)


@packet(id=12, since=2168)
class AddPlayerPacket:
    uuid: uuid.UUID
    name: str
    runtime_id: ActorRuntimeID
    platform_online_id: str
    pos: Vec3
    velocity: Vec3
    rot: Vec2
    y_head_rot: float
    carried_item: SerializedNetworkItemStackDescriptor
    player_game_type: GameType
    unpack: SynchedActorData.CopyableDataList
    synched_properties: PropertySyncData
    abilities_data: SerializedAbilitiesData
    links: list[ActorLink]
    device_id: str
    build_platform: BuildPlatform = field(type=int32)
