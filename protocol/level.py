from protocol._dsl import field, packet
from protocol.common import BlockPos, SubChunkPos, int8, uint32, varint32
from protocol.nbt import CompoundTag

package = "bedrock.protocol"

type DimensionType = varint32


class DimensionDefinition:
    name: str
    height_maximum: varint32
    height_minimum: varint32
    generator_type: varint32
    dimension_type: DimensionType = field(since=975)


@packet(id=180, since=503)
class DimensionDataPacket:
    """Describes the data-driven dimensions a server has registered."""

    definitions: list[DimensionDefinition]


@packet(id=56)
class BlockActorDataPacket:
    """Updates the NBT data of the block entity at a position."""

    block_position: BlockPos
    actor_data_tags: CompoundTag


class SubChunkPosOffset:
    x: int8
    y: int8
    z: int8


@packet(id=175, since=471)
class SubChunkRequestPacket:
    """Asks the server for sub-chunks around a center position. The offset list
    that batches multiple sub-chunks into one request arrived at protocol 486."""

    dimension_type: DimensionType
    center_pos: SubChunkPos
    sub_chunk_pos_offsets: list[SubChunkPosOffset] = field(
        prefix=uint32, since=486
    )
