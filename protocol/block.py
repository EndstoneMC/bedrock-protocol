"""The level's block space: world/level/block/ -- blocks, block actors, sub-chunk
block changes, the level events fired over them, and world/level/voxelshape/ volumes.
Not chunk transfer -- world/level/chunk/, in chunk.py."""

from enum import IntEnum

from protocol import field, int32, packet, type, uint8, uint16, uint32, uvarint32, uvarint64, varint32
from protocol.actor import ActorUniqueID
from protocol.common import BlockPos, DimensionType, Vec3
from protocol.nbt import CompoundTag
from protocol.network import NetworkBlockPosition

package = "bedrock.protocol"


@packet(id=141, until=944)
class AnvilDamagePacket:
    damage: int32 = field(type=uint8)
    position: NetworkBlockPosition


@packet(id=141, since=944)
class AnvilDamagePacket:
    damage: int32 = field(type=uint8, until=2168)
    position: BlockPos


@packet(id=21, until=944)
class UpdateBlockPacket:
    pos: NetworkBlockPosition
    runtime_id: uvarint32
    update_flags: uint8 = field(type=uvarint32)
    layer: uvarint32


@packet(id=21, since=944)
class UpdateBlockPacket:
    pos: BlockPos
    runtime_id: uvarint32
    update_flags: uint8 = field(type=uvarint32)
    layer: uvarint32


@packet(id=26, until=944)
class BlockEventPacket:
    pos: NetworkBlockPosition
    b0: varint32
    b1: varint32


@packet(id=26, since=944)
class BlockEventPacket:
    pos: BlockPos
    b0: varint32
    b1: varint32


@packet(id=34)
class BlockPickRequestPacket:
    pos: BlockPos
    with_data: bool
    max_slots: uint8


@packet(id=56, until=944)
class BlockActorDataPacket:
    pos: NetworkBlockPosition
    data: CompoundTag


@packet(id=56, since=944)
class BlockActorDataPacket:
    pos: BlockPos
    data: CompoundTag


class ActorBlockSyncMessage:
    class MessageId(IntEnum, uint32):
        NONE = 0
        CREATE = 1
        DESTROY = 2


@packet(id=110, until=944)
class UpdateBlockSyncedPacket:
    pos: NetworkBlockPosition
    runtime_id: uvarint32
    update_flags: uint8 = field(type=uvarint32)
    layer: uvarint32
    entity_unique_id: ActorUniqueID = field(type=uvarint64)
    message: ActorBlockSyncMessage.MessageId = field(type=uvarint64)


@packet(id=110, since=944)
class UpdateBlockSyncedPacket:
    pos: BlockPos
    runtime_id: uvarint32
    update_flags: uint8 = field(type=uvarint32)
    layer: uvarint32
    entity_unique_id: ActorUniqueID = field(type=uvarint64)
    message: ActorBlockSyncMessage.MessageId = field(type=uvarint64)


@packet(id=125, until=944)
class LecternUpdatePacket:
    page: int32 = field(type=uint8)
    total_pages: int32 = field(type=uint8)
    pos: NetworkBlockPosition


@packet(id=125, since=944)
class LecternUpdatePacket:
    page: int32 = field(type=uint8)
    total_pages: int32 = field(type=uint8)
    pos: BlockPos


@packet(id=303, until=944)
class OpenSignPacket:
    pos: NetworkBlockPosition
    is_front_side: bool


@packet(id=303, since=944)
class OpenSignPacket:
    pos: BlockPos
    is_front_side: bool


@type(until=944)
class UpdateSubChunkNetworkBlockInfo:
    pos: NetworkBlockPosition
    runtime_id: uvarint32
    update_flags: uint8 = field(type=uvarint32)
    entity_unique_id: ActorUniqueID = field(type=uvarint64)
    message: ActorBlockSyncMessage.MessageId


@type(since=944)
class UpdateSubChunkNetworkBlockInfo:
    pos: BlockPos
    runtime_id: uvarint32
    update_flags: uint8 = field(type=uvarint32)
    entity_unique_id: ActorUniqueID = field(type=uvarint64)
    message: ActorBlockSyncMessage.MessageId


class UpdateSubChunkBlocksChangedInfo:
    standards: list[UpdateSubChunkNetworkBlockInfo]
    extras: list[UpdateSubChunkNetworkBlockInfo]


@packet(id=172, until=944)
class UpdateSubChunkBlocksPacket:
    sub_chunk_block_position: NetworkBlockPosition
    blocks_changed: UpdateSubChunkBlocksChangedInfo


@packet(id=172, since=944)
class UpdateSubChunkBlocksPacket:
    sub_chunk_block_position: BlockPos
    blocks_changed: UpdateSubChunkBlocksChangedInfo


type EntityNetId = uvarint32


@packet(id=167)
class RemoveVolumeEntityPacket:
    entity_net_id: EntityNetId
    dimension_type: DimensionType


@packet(id=166, until=944)
class AddVolumeEntityPacket:
    entity_net_id: EntityNetId
    components: CompoundTag
    json_identifier: str
    instance_name: str
    min_bounds: NetworkBlockPosition
    max_bounds: NetworkBlockPosition
    dimension_type: DimensionType
    min_engine_version: str


@packet(id=166, since=944)
class AddVolumeEntityPacket:
    entity_net_id: EntityNetId
    components: CompoundTag
    json_identifier: str
    instance_name: str
    min_bounds: BlockPos
    max_bounds: BlockPos
    dimension_type: DimensionType
    min_engine_version: str


type RegistryHandle = uint16


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
    shapes: list[SerializableVoxelShape]
    name_map: dict[str, RegistryHandle]
    custom_shape_count: uint16 = field(since=944)


@packet(id=25)
class LevelEventPacket:
    event_id: varint32
    pos: Vec3
    data: varint32


@packet(id=124)
class LevelEventGenericPacket:
    event_id: varint32
    data: CompoundTag


@packet(id=118)
class SpawnParticleEffectPacket:
    vanilla_dimension_id: uint8
    actor_id: ActorUniqueID
    pos: Vec3
    effect_name: str
    molang_variables: str | None
