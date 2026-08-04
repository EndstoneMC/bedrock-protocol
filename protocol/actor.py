from enum import IntEnum

from protocol import int8, int16, packet, type, uint8, uvarint32, uvarint64, varint32, varint64
from protocol.common import BlockPos, Vec2, Vec3
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


type ActorUniqueID = varint64
type ActorRuntimeID = uvarint64
type PlayerInputTick = uvarint64


class DataItemType(IntEnum, uint8):
    BYTE = 0
    SHORT = 1
    INT = 2
    FLOAT = 3
    STRING = 4
    COMPOUND_TAG = 5
    POS = 6
    INT64 = 7
    VEC3 = 8
    UNKNOWN = 9


@type(until=2168)
class DataItemBytePayload:
    value: int8


@type(since=2168)
class DataItemBytePayload:
    type: DataItemType
    value: int8


@type(until=2168)
class DataItemShortPayload:
    value: int16


@type(since=2168)
class DataItemShortPayload:
    type: DataItemType
    value: int16


@type(until=2168)
class DataItemIntPayload:
    value: varint32


@type(since=2168)
class DataItemIntPayload:
    type: DataItemType
    value: varint32


@type(until=2168)
class DataItemFloatPayload:
    value: float


@type(since=2168)
class DataItemFloatPayload:
    type: DataItemType
    value: float


@type(until=2168)
class DataItemStringPayload:
    value: str


@type(since=2168)
class DataItemStringPayload:
    type: DataItemType
    value: str


@type(until=2168)
class DataItemCompoundTagPayload:
    value: CompoundTag


@type(since=2168)
class DataItemCompoundTagPayload:
    type: DataItemType
    value: CompoundTag


@type(until=2168)
class DataItemPosPayload:
    value: BlockPos


@type(since=2168)
class DataItemPosPayload:
    type: DataItemType
    value: BlockPos


@type(until=2168)
class DataItemInt64Payload:
    value: varint64


@type(since=2168)
class DataItemInt64Payload:
    type: DataItemType
    value: varint64


@type(until=2168)
class DataItemVec3Payload:
    value: Vec3


@type(since=2168)
class DataItemVec3Payload:
    type: DataItemType
    value: Vec3


class DataItemEntry:
    id: uvarint32
    payload: (
        DataItemBytePayload
        | DataItemShortPayload
        | DataItemIntPayload
        | DataItemFloatPayload
        | DataItemStringPayload
        | DataItemCompoundTagPayload
        | DataItemPosPayload
        | DataItemInt64Payload
        | DataItemVec3Payload
    )


class SynchedActorData:
    class CopyableDataList:
        data: list[DataItemEntry]


class PropertySyncData:
    class PropertySyncIntEntry:
        property_index: uvarint32
        data: varint32

    class PropertySyncFloatEntry:
        property_index: uvarint32
        data: float

    int_entries: list[PropertySyncIntEntry]
    float_entries: list[PropertySyncFloatEntry]


class SyncedAttribute:
    name: str
    min_value: float
    current_value: float
    max_value: float


class ActorLinkType(IntEnum, uint8):
    NONE = 0
    RIDING = 1
    PASSENGER = 2


class ActorLink:
    a: ActorUniqueID
    b: ActorUniqueID
    type: ActorLinkType
    immediate: bool
    passenger_initiated: bool
    vehicle_angular_velocity: float


@packet(id=13)
class AddActorPacket:
    entity_id: ActorUniqueID
    runtime_id: ActorRuntimeID
    type: str
    pos: Vec3
    velocity: Vec3
    rot: Vec2
    y_head_rotation: float
    y_body_rotation: float
    attributes: list[SyncedAttribute]
    data: SynchedActorData.CopyableDataList
    synched_properties: PropertySyncData
    links: list[ActorLink]


@packet(id=39)
class SetActorDataPacket:
    id: ActorRuntimeID
    packed_items: SynchedActorData.CopyableDataList
    synched_properties: PropertySyncData
    tick: PlayerInputTick
