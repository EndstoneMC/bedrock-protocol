from protocol import field, int8, packet, uint32, varint32
from protocol.common import BlockPos, SubChunkPos
from protocol.nbt import CompoundTag

package = "bedrock.protocol"

type DimensionType = varint32


class DimensionDefinition:
    name: str
    height_maximum: varint32
    height_minimum: varint32
    generator_type: varint32
    dimension_type: DimensionType = field(since=975)


# TODO: absent from EndstoneMC/protocol-docs r26_u3 (v1001) -- renamed or
# removed after v975. Investigate when bumping past v975 and decide whether
# to add `until=` here or rename the packet to match BDS r26_u3.
@packet(id=180, since=503)
class DimensionDataPacket:
    definitions: list[DimensionDefinition]


@packet(id=56)
class BlockActorDataPacket:
    """Sends the entire user data compound tag and the block position to the client."""

    pos: BlockPos
    data: CompoundTag


class SubChunkPosOffset:
    x: int8
    y: int8
    z: int8


@packet(id=175, since=471)
class SubChunkRequestPacket:
    dimension_type: DimensionType
    center_pos: SubChunkPos
    sub_chunk_pos_offsets: list[SubChunkPosOffset] = field(prefix=uint32, since=486)
