"""Chunk and sub-chunk transfer, radius negotiation, publisher updates:
world/level/chunk/."""

from enum import IntEnum

from protocol import array, field, int8, int32, packet, type, uint8, uint16, uint32, uint64, uvarint32, varint32
from protocol.common import BlockPos, DimensionType

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


@packet(id=174, until=2168)
class SubChunkPacket:
    class HeightMapDataType(IntEnum, uint8):
        NO_DATA = 0
        HAS_DATA = 1
        ALL_TOO_HIGH = 2
        ALL_TOO_LOW = 3
        ALL_COPIED = 4

    class SubChunkRequestResult(IntEnum, uint8):
        UNDEFINED = 0
        SUCCESS = 1
        LEVEL_CHUNK_DOESNT_EXIST = 2
        WRONG_DIMENSION = 3
        PLAYER_DOESNT_EXIST = 4
        INDEX_OUT_OF_BOUNDS = 5
        SUCCESS_ALL_AIR = 6

    class HeightmapData:
        height_map_type: HeightMapDataType
        subchunk_height_map: array[array[int8, 16], 16] = field(
            when=lambda h: h.height_map_type == HeightMapDataType.HAS_DATA
        )
        render_height_map_type: HeightMapDataType
        subchunk_render_height_map: array[array[int8, 16], 16] = field(
            when=lambda h: h.render_height_map_type == HeightMapDataType.HAS_DATA
        )

    class SubChunkPosOffset:
        x: int8
        y: int8
        z: int8

    class SubChunkPacketData:
        sub_chunk_pos_offset: SubChunkPosOffset
        result: SubChunkRequestResult
        serialized_sub_chunk: str = field(when=lambda d: d.result != SubChunkRequestResult.SUCCESS_ALL_AIR)
        height_map_data: HeightmapData
        blob_id: uint64

    @type(until=2168)
    class UncachedSubChunkPacketData:
        sub_chunk_pos_offset: SubChunkPosOffset
        result: SubChunkRequestResult
        serialized_sub_chunk: str
        height_map_data: HeightmapData

    cache_enabled: bool
    dimension_type: DimensionType
    # TODO: mCenterPos is a SubChunkPos, but this packet does not cerealise until 2168, so here
    # it writes three varint32 where the cerealised SubChunkPos (chunk.py:20, reached by packet
    # 175 from 1001 on) is three fixed int32. The DSL versions a type by protocol version, not
    # by writer, so the components are spelled out.
    center_pos_x: varint32
    center_pos_y: varint32
    center_pos_z: varint32
    with field(when=lambda p: p.cache_enabled):
        sub_chunk_data: list[SubChunkPacketData] = field(prefix=uint32)
    with field(when=lambda p: not p.cache_enabled):
        uncached_sub_chunk_data: list[UncachedSubChunkPacketData] = field(prefix=uint32)


@packet(id=174, since=2168)
class SubChunkPacket:
    class HeightMapDataType(IntEnum, uint8):
        NO_DATA = 0
        HAS_DATA = 1
        ALL_TOO_HIGH = 2
        ALL_TOO_LOW = 3
        ALL_COPIED = 4

    class SubChunkRequestResult(IntEnum, uint8):
        UNDEFINED = 0
        SUCCESS = 1
        LEVEL_CHUNK_DOESNT_EXIST = 2
        WRONG_DIMENSION = 3
        PLAYER_DOESNT_EXIST = 4
        INDEX_OUT_OF_BOUNDS = 5
        SUCCESS_ALL_AIR = 6

    @type(since=2168, until=2192)
    class HeightmapData:
        height_map_type: HeightMapDataType
        subchunk_height_map: array[array[int8, 16], 16] | None
        render_height_map_type: HeightMapDataType
        subchunk_render_height_map: array[array[int8, 16], 16] | None

    @type(since=2192)
    class HeightmapData:
        height_map_type: HeightMapDataType
        subchunk_height_map: array[list[int8], 16] | None
        render_height_map_type: HeightMapDataType
        subchunk_render_height_map: array[list[int8], 16] | None

    class SubChunkPosOffset:
        x: int8
        y: int8
        z: int8

    class SubChunkPacketData:
        sub_chunk_pos_offset: SubChunkPosOffset
        result: SubChunkRequestResult
        serialized_sub_chunk: str | None
        height_map_data: HeightmapData
        blob_id: uint64 | None

    cache_enabled: bool
    dimension_type: DimensionType
    center_pos: SubChunkPos
    sub_chunk_data: list[SubChunkPacketData]


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


@packet(id=69, since=2168)
class RequestChunkRadiusPacket:
    chunk_radius: varint32
    max_chunk_radius: uint8


@packet(id=70, since=2168)
class ChunkRadiusUpdatedPacket:
    chunk_radius: varint32


@packet(id=121, since=2168)
class NetworkChunkPublisherUpdatePacket:
    position: BlockPos
    radius: uvarint32
    server_built_chunks: list[ChunkPos] = field(prefix=uint32)
