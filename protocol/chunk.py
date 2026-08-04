from protocol import field, int8, int32, packet, type, uint16, uint32, uint64, uvarint32, varint32
from protocol.attributes import DimensionType

package = "bedrock.protocol"


class ChunkPos:
    x: varint32
    z: varint32


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


@packet(id=58, until=2168)
class LevelChunkPacket:
    class SubChunkMetadata:
        blob_id: uint64

    pos: ChunkPos
    dimension_id: DimensionType
    sub_chunks_count: uvarint32
    client_request_sub_chunk_limit: uint16 = field(when=lambda p: p.sub_chunks_count == 4294967294)
    cache_enabled: bool
    cache_metadata: list[SubChunkMetadata] = field(when=lambda p: p.cache_enabled)
    serialized_chunk: str


@packet(id=58, since=2168)
class LevelChunkPacket:
    class SubChunkMetadata:
        blob_id: uint64

    pos: ChunkPos
    dimension_id: DimensionType
    sub_chunks_count: uvarint32
    client_request_sub_chunk_limit: varint32 | None
    cache_enabled: bool
    cache_metadata: list[SubChunkMetadata]
    serialized_chunk: str


# TODO: packet 174 is unmodelled. Its 2168 form needs field(count=) inside an
# optional, and its 1001 form needs field(when=) to reach the enclosing packet's
# cache_enabled. Only the nested type below is modelled.
class SubChunkPacket:
    class SubChunkPosOffset:
        x: int8
        y: int8
        z: int8


@packet(id=175, until=1001)
class SubChunkRequestPacket:
    dimension_type: DimensionType
    center_pos: SubChunkPos
    sub_chunk_pos_offsets: list[SubChunkPacket.SubChunkPosOffset] = field(prefix=uint32)


@packet(id=175, since=1001)
class SubChunkRequestPacket:
    dimension_type: DimensionType
    sub_chunk_pos_offsets: list[SubChunkPacket.SubChunkPosOffset]
    center_pos: SubChunkPos
