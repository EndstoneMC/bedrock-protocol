import uuid
from enum import IntEnum

from protocol import array, bitset, field, int8, int32, int64, packet, type, uint8, uint16, uint32, uvarint64
from protocol.actor import (
    ActorLink,
    ActorRuntimeID,
    ActorUniqueID,
    PlayerInputTick,
    PropertySyncData,
    SynchedActorData,
)
from protocol.command import CommandPermissionLevel
from protocol.common import Vec2, Vec3
from protocol.game import GameType, PlayerPermissionLevel
from protocol.inventory import NetworkItemStackDescriptor, SerializedNetworkItemStackDescriptor
from protocol.player_list import BuildPlatform

package = "bedrock.protocol"


class SerializedAbilitiesData:
    class SerializedAbilitiesLayer(IntEnum, uint16):
        CUSTOM_CACHE = 0
        BASE = 1
        SPECTATOR = 2
        COMMANDS = 3
        EDITOR = 4
        LOADING_SCREEN = 5

    class SerializedLayer:
        serialized_layer: SerializedAbilitiesLayer = field(type=uint16)
        abilities_set: uint32
        ability_values: uint32
        fly_speed: float
        vertical_fly_speed: float
        walk_speed: float

    target_player: ActorUniqueID = field(type=int64)
    player_permissions: PlayerPermissionLevel
    command_permissions: CommandPermissionLevel
    layers: list[SerializedLayer]


class PlayerPositionModeComponent:
    class PositionMode(IntEnum, uint8):
        NORMAL = 0
        RESPAWN = 1
        TELEPORT = 2
        ONLY_HEAD_ROT = 3


@type(since=2168)
class MovePlayerTeleportData:
    cause: int32
    source_entity_type: int32


@type(until=2168)
class MoveActorDeltaData:
    runtime_id: ActorRuntimeID
    header: uint16
    new_position_x: float = field(when=lambda d: d.header & 1 != 0)
    new_position_y: float = field(when=lambda d: d.header & 2 != 0)
    new_position_z: float = field(when=lambda d: d.header & 4 != 0)
    rot_x: int8 = field(when=lambda d: d.header & 8 != 0)
    rot_y: int8 = field(when=lambda d: d.header & 16 != 0)
    rot_y_head: int8 = field(when=lambda d: d.header & 32 != 0)


@type(since=2168)
class MoveActorDeltaData:
    runtime_id: ActorRuntimeID
    new_position_x: float | None
    new_position_y: float | None
    new_position_z: float | None
    rot_x: int8 | None
    rot_y: int8 | None
    rot_y_head: int8 | None
    is_on_ground: bool
    force_move: bool
    force_move_local_entity: bool
    force_completion: bool
    ticks: uvarint64 = field(since=2192)


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


@packet(id=15, until=2168)
class AddItemActorPacket:
    id: ActorUniqueID
    runtime_id: ActorRuntimeID
    item: NetworkItemStackDescriptor
    pos: Vec3
    velocity: Vec3
    data: SynchedActorData.CopyableDataList
    is_from_fishing: bool


@packet(id=15, since=2168)
class AddItemActorPacket:
    id: ActorUniqueID
    runtime_id: ActorRuntimeID
    item: SerializedNetworkItemStackDescriptor
    pos: Vec3
    velocity: Vec3
    data: SynchedActorData.CopyableDataList
    is_from_fishing: bool


@packet(id=19, until=2168)
class MovePlayerPacket:
    player_id: ActorRuntimeID
    pos: Vec3
    rot: Vec2
    y_head_rot: float
    reset_position: PlayerPositionModeComponent.PositionMode
    on_ground: bool
    riding_id: ActorRuntimeID

    with field(when=lambda p: p.reset_position == PlayerPositionModeComponent.PositionMode.TELEPORT):
        cause: int32
        source_entity_type: int32

    tick: PlayerInputTick


@packet(id=19, since=2168)
class MovePlayerPacket:
    player_id: ActorRuntimeID
    pos: Vec3
    rot: Vec2
    y_head_rot: float
    reset_position: PlayerPositionModeComponent.PositionMode
    on_ground: bool
    riding_id: ActorRuntimeID
    teleport_data: MovePlayerTeleportData | None
    tick: PlayerInputTick


@packet(id=111)
class MoveActorDeltaPacket:
    move_data: MoveActorDeltaData


@packet(id=16, since=2168)
class ServerPlayerPostMovePositionPacket:
    pos: Vec3


class ActorDataFlagComponent:
    value: bitset[131]


class ActorDataBoundingBoxComponent:
    value: array[float, 3]


@packet(id=322, since=2168)
class ClientMovementPredictionSyncPacket:
    actor_data_flag: ActorDataFlagComponent
    actor_bounding_box: ActorDataBoundingBoxComponent
    movement_attributes: array[float, 9]
    actor_id: ActorUniqueID
    is_flying: bool
