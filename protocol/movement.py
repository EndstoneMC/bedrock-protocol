"""Position and movement over the wire: move, teleport, delta moves, prediction
correction and sync. Not actor or player spawning -- AddPlayerPacket is in player.py
and AddItemActorPacket in actor.py."""

from enum import IntEnum

from protocol import array, bitset, field, int8, int32, packet, type, uint8, uint16, uvarint64
from protocol.actor import ActorFlags, ActorRuntimeID, ActorUniqueID, PlayerInputTick
from protocol.common import Vec2, Vec3

package = "bedrock.protocol"


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


@packet(id=16)
class ServerPlayerPostMovePositionPacket:
    pos: Vec3


class ActorDataFlagComponent:
    value: bitset[ActorFlags.COUNT]


class ActorDataBoundingBoxComponent:
    value: array[float, 3]


@packet(id=322, until=975)
class ClientMovementPredictionSyncPacket:
    actor_data_flag: ActorDataFlagComponent
    actor_bounding_box: ActorDataBoundingBoxComponent
    movement_attributes: array[float, 6]
    actor_id: ActorUniqueID
    is_flying: bool


@packet(id=322, since=975)
class ClientMovementPredictionSyncPacket:
    actor_data_flag: ActorDataFlagComponent
    actor_bounding_box: ActorDataBoundingBoxComponent
    movement_attributes: array[float, 9]
    actor_id: ActorUniqueID
    is_flying: bool


class RewindType(IntEnum, uint8):
    PLAYER = 0
    VEHICLE = 1


@packet(id=161, until=827)
class CorrectPlayerMovePredictionPacket:
    prediction_type: RewindType
    pos: Vec3
    pos_delta: Vec3
    with field(when=lambda p: p.prediction_type == RewindType.VEHICLE):
        vehicle_rotation: Vec2
        vehicle_angular_velocity: float | None
    on_ground: bool
    tick: PlayerInputTick


@packet(id=161, since=827)
class CorrectPlayerMovePredictionPacket:
    prediction_type: RewindType
    pos: Vec3
    pos_delta: Vec3
    vehicle_rotation: Vec2
    vehicle_angular_velocity: float | None
    on_ground: bool
    tick: PlayerInputTick
