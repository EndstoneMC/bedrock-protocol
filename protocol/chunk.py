from protocol import field, int8, int32, packet, type, uint32, varint32
from protocol.attributes import DimensionType

package = "bedrock.protocol"


@type(until=1001)
class SubChunkPos:
    x: varint32
    y: varint32
    z: varint32


@type(since=1001)
class SubChunkPos:
    x: int32
    y: int32
    z: int32


# BDS nests this in SubChunkPacket, which is not modelled; hoisted, keeping the
# BDS name.
class SubChunkPosOffset:
    x: int8
    y: int8
    z: int8


@packet(id=175, until=1001)
class SubChunkRequestPacket:
    dimension_type: DimensionType
    center_pos: SubChunkPos
    sub_chunk_pos_offsets: list[SubChunkPosOffset] = field(prefix=uint32)


@packet(id=175, since=1001)
class SubChunkRequestPacket:
    dimension_type: DimensionType
    sub_chunk_pos_offsets: list[SubChunkPosOffset]
    center_pos: SubChunkPos
