"""The level's block space: world/level/block/ -- blocks, block actors, sub-chunk
block changes, the level events fired over them, and world/level/voxelshape/ volumes.
Not chunk transfer -- world/level/chunk/, in chunk.py."""

from enum import IntEnum

from protocol import field, int32, packet, uint8, uint16, uint32, uvarint32, uvarint64, varint32
from protocol.actor import ActorUniqueID
from protocol.common import BlockPos, BlockRuntimeId, DimensionType, Vec3
from protocol.nbt import CompoundTag, CompoundTagData
from protocol.network import NetworkBlockPosition

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"


@packet(id=141)
class AnvilDamagePacket:
    damage: int32 = field(type=uint8, until=2168)
    position: NetworkBlockPosition = field(until=944)
    position: BlockPos = field(since=944)


@packet(id=21)
class UpdateBlockPacket:
    pos: NetworkBlockPosition = field(until=944)
    pos: BlockPos = field(since=944)
    runtime_id: BlockRuntimeId
    update_flags: uint8 = field(type=uvarint32)
    layer: uvarint32


@packet(id=26)
class BlockEventPacket:
    pos: NetworkBlockPosition = field(until=944)
    pos: BlockPos = field(since=944)
    b0: varint32
    b1: varint32


@packet(id=34)
class BlockPickRequestPacket:
    pos: BlockPos
    with_data: bool
    max_slots: uint8


@packet(id=56)
class BlockActorDataPacket:
    pos: NetworkBlockPosition = field(until=944)
    pos: BlockPos = field(since=944)
    data: CompoundTag


class ActorBlockSyncMessage:
    class MessageId(IntEnum, uint32):
        NONE = 0
        CREATE = 1
        DESTROY = 2


@packet(id=110)
class UpdateBlockSyncedPacket:
    pos: NetworkBlockPosition = field(until=944)
    pos: BlockPos = field(since=944)
    runtime_id: BlockRuntimeId
    update_flags: uint8 = field(type=uvarint32)
    layer: uvarint32
    entity_unique_id: ActorUniqueID = field(type=uvarint64)
    message: ActorBlockSyncMessage.MessageId = field(type=uvarint64)


@packet(id=125)
class LecternUpdatePacket:
    page: int32 = field(type=uint8)
    total_pages: int32 = field(type=uint8)
    pos: NetworkBlockPosition = field(until=944)
    pos: BlockPos = field(since=944)


@packet(id=303)
class OpenSignPacket:
    pos: NetworkBlockPosition = field(until=944)
    pos: BlockPos = field(since=944)
    is_front_side: bool


class UpdateSubChunkNetworkBlockInfo:
    pos: NetworkBlockPosition = field(until=944)
    pos: BlockPos = field(since=944)
    runtime_id: BlockRuntimeId
    update_flags: uint8 = field(type=uvarint32)
    entity_unique_id: ActorUniqueID = field(type=uvarint64)
    message: ActorBlockSyncMessage.MessageId


class UpdateSubChunkBlocksChangedInfo:
    standards: list[UpdateSubChunkNetworkBlockInfo]
    extras: list[UpdateSubChunkNetworkBlockInfo]


@packet(id=172)
class UpdateSubChunkBlocksPacket:
    sub_chunk_block_position: NetworkBlockPosition = field(until=944)
    sub_chunk_block_position: BlockPos = field(since=944)
    blocks_changed: UpdateSubChunkBlocksChangedInfo


type EntityNetId = uvarint32


@packet(id=167)
class RemoveVolumeEntityPacket:
    entity_net_id: EntityNetId
    dimension_type: DimensionType


@packet(id=166)
class AddVolumeEntityPacket:
    entity_net_id: EntityNetId
    components: CompoundTag
    json_identifier: str
    instance_name: str
    with field(until=944):
        min_bounds: NetworkBlockPosition
        max_bounds: NetworkBlockPosition
    with field(since=944):
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
    data: CompoundTagData


@packet(id=118)
class SpawnParticleEffectPacket:
    vanilla_dimension_id: uint8
    actor_id: ActorUniqueID
    pos: Vec3
    effect_name: str
    molang_variables: str | None
