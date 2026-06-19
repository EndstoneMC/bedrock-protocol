from enum import IntEnum

from protocol import (
    field,
    int8,
    int32,
    int64,
    packet,
    type,
    uint8,
    uint16,
    uint32,
    uint64,
    uvarint32,
    uvarint64,
    varint32,
)
from protocol.actor import ActorRuntimeID
from protocol.common import BlockPos, NetworkBlockPos, Vec3
from protocol.dimension import DimensionType
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


type PositionTrackingId = varint32


@packet(id=154, since=407)
class PositionTrackingDBClientRequestPacket:
    """Client to server packet for server authoritative runtime database (with persistent
    LevelStorage backup) designed primarily to track lodestone stuff."""

    class Action(IntEnum):
        QUERY = 0

    action: Action = field(type=uint8)
    id: PositionTrackingId


@packet(id=153, since=407)
class PositionTrackingDBServerBroadcastPacket:
    """Server to client packet for server authoritative runtime database (with persistent
    LevelStorage backup) designed primarily to track lodestone stuff."""

    class Action(IntEnum):
        UPDATE = 0
        DESTROY = 1
        NOT_FOUND = 2

    action: Action = field(type=uint8)
    id: PositionTrackingId
    data: CompoundTag


@packet(id=56)
class BlockActorDataPacket:
    """Sends the entire user data compound tag and the block position to the client."""

    pos: NetworkBlockPos = field(until=944)
    pos: BlockPos = field(since=944)
    data: CompoundTag


@packet(id=26)
class BlockEventPacket:
    """Whenever a block event happens it is sent from the server to sync client and server,
    with arbitrarily encoded information in b0 and b1."""

    pos: NetworkBlockPos = field(until=944)
    pos: BlockPos = field(since=944)
    b0: varint32
    b1: varint32


@packet(id=70)
class ChunkRadiusUpdatedPacket:
    chunk_radius: varint32


# ExplodePacket (id=23, removed at v388) is omitted: lone @packet(until=) is
# not expressible in the DSL today, and the same id is reused by TickSyncPacket
# in [388, 685).


class ChunkPos:
    x: varint32
    z: varint32


class SubChunkMetadata:
    blob_id: uint64


@packet(id=58)
class LevelChunkPacket:
    pos: ChunkPos
    dimension_id: DimensionType = field(since=649)
    # At v486+ the uvarint32 sub-chunk count carries two sentinel values:
    # 0xFFFFFFFF = "request mode limitless" (no trailer), 0xFFFFFFFE = "request
    # mode limited" followed by a uint16 LE highest-sub-chunk index. The trailer
    # is gated by comparing the raw wire integer against the sentinel.
    sub_chunks_count: uvarint32
    highest_sub_chunk: uint16 = field(
        when=lambda p: p.sub_chunks_count == 0xFFFFFFFE,
        since=486,
    )
    cache_enabled: bool
    cache_blobs: list[SubChunkMetadata] = field(when=lambda p: p.cache_enabled)
    serialized_chunk: bytes


type LevelEvent = varint32


@packet(id=25)
class LevelEventPacket:
    """Splash Potions, weather events, global pause, simlock commands, oh my!"""

    event_id: LevelEvent
    pos: Vec3
    data: varint32


@packet(id=124, since=361)
class LevelEventGenericPacket:
    event_id: LevelEvent
    data: CompoundTag


type LevelSoundEvent = uvarint32


@packet(id=123, since=332)
class LevelSoundEventPacket:
    """Most sounds get launched on server and replicated to clients, but a handful of player
    initiated sounds are launched on their client and replicated through the network."""

    # v1001 replaced the uvarint32 enum ordinal with the lower-cased sound-event
    # name as a length-prefixed string (e.g. "item.use.on", "fall.big").
    event_id: LevelSoundEvent = field(until=1001)
    event_id: str = field(since=1001)
    pos: Vec3
    data: varint32
    actor_identifier: str
    is_baby: bool
    is_global: bool
    # BDS names this mActor (ActorUniqueID), but the wire encodes it as a little-endian int64,
    # not the usual varint64.
    actor: int64 = field(since=786)
    fire_at_position: Vec3 | None = field(since=975)


# LevelSoundEventV1Packet (id=24) and LevelSoundEventV2Packet (id=120, v313..v786)
# are omitted: both were removed before v975 and the DSL cannot express a lone
# @packet(until=) today.


@packet(id=121, since=313)
class NetworkChunkPublisherUpdatePacket:
    """Tells clients to update the chunk view for the local player."""

    position: BlockPos
    radius: uvarint32
    server_built_chunks: list[ChunkPos] = field(prefix=uint32, since=544)


@packet(id=86)
class PlaySoundPacket:
    """This packet is only used via command or script event. This is for 3rd party content."""

    name: str
    pos: BlockPos
    volume: float
    pitch: float
    server_sound_handle: uint64 | None = field(since=975)


@type(since=1001)
class SoundDataEvent(IntEnum):
    STOP = 0


@packet(id=348, since=1001)
class ClientboundUpdateSoundDataPacket:
    server_sound_handle: uint64
    sound_event: SoundDataEvent = field(type=str)


@packet(id=69)
class RequestChunkRadiusPacket:
    """The client can't just change the view radius without the server's approval, otherwise
    there could be holes on unrendered area."""

    chunk_radius: varint32
    max_chunk_radius: uint8 = field(since=582)


class PlayerRespawnState(IntEnum):
    SEARCHING_FOR_SPAWN = 0
    READY_TO_SPAWN = 1
    CLIENT_READY_TO_SPAWN = 2


@packet(id=45)
class RespawnPacket:
    pos: Vec3
    state: PlayerRespawnState = field(type=uint8, since=388)
    runtime_id: ActorRuntimeID = field(since=388)


class SpawnPositionType(IntEnum):
    PLAYER_RESPAWN = 0
    WORLD_SPAWN = 1


@packet(id=43)
class SetSpawnPositionPacket:
    """When a player logs in or the SetWorldSpawnCommand is used this is sent from the server
    to the client. Does not change when using a bed, that is a separate packet (RespawnPacket)."""

    spawn_pos_type: SpawnPositionType = field(type=uvarint32)
    pos: NetworkBlockPos = field(until=944)
    pos: BlockPos = field(since=944)
    spawn_forced: bool = field(until=407)
    dimension_type: DimensionType = field(since=407)
    spawn_block_pos: NetworkBlockPos = field(since=407, until=944)
    spawn_block_pos: BlockPos = field(since=944)


@packet(id=87)
class StopSoundPacket:
    """Allows you to stop a sound or all sounds on all clients, only used in a /command."""

    name: str
    stop_all: bool
    stop_music_legacy: bool = field(since=712)


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


class SubChunkPosOffset:
    x: int8
    y: int8
    z: int8


# SubChunkPacket (id=174) is omitted: its v471..v486 incremental wire shapes
# require cross-struct predicates (the per-entry payload is gated by the
# packet-level cache_enabled flag) and lone @packet(until=) on the legacy
# fields. SubChunkRequestPacket (id=175) below covers the request half.


# COMPILER_EXTENSION_NEEDED: the v1001 cereal migration reorders the two
# trailing fields -- the offset list moved ahead of the center position and its
# length prefix narrowed from a fixed uint32 to a uvarint32 (SubChunkPos itself
# also switched to fixed int32 coords, see protocol/common.py). Expressing this
# needs two compiler features the redeclaration path lacks today:
#   1. Per-version field ordering. parser.py merges a redeclared class to a
#      single canonical order (the latest declaration's) and emits it for every
#      version, so the pre-1001 wire would be written in the v1001 order. A
#      version that reorders shared fields cannot be modelled until the merge
#      keeps a per-version order.
#   2. A field(since=) gate inside a redeclared class (the offsets `since=486`
#      below), which the resolver currently rejects.
# Until both land, this packet does not codegen; the two @packet forms below are
# the intended v1001 wire shape, kept as the spec.
@packet(id=175, since=471, until=1001)
class SubChunkRequestPacket:
    """Sent from the client to the server representing a batch of subchunks that the client requests from the server."""

    dimension_type: DimensionType
    center_pos: SubChunkPos
    sub_chunk_pos_offsets: list[SubChunkPosOffset] = field(prefix=uint32, since=486)


@packet(id=175, since=1001)
class SubChunkRequestPacket:
    """Sent from the client to the server representing a batch of subchunks that the client requests from the server."""

    dimension_type: DimensionType
    sub_chunk_pos_offsets: list[SubChunkPosOffset]
    center_pos: SubChunkPos


type BlockRuntimeId = uvarint32


class UpdateBlockFlags(IntEnum):
    """Bit flags packed into the `update_flags` field of UpdateBlock*Packet."""

    NEIGHBORS = 0x01
    NETWORK = 0x02
    NO_GRAPHIC = 0x04
    UNUSED = 0x08
    PRIORITY = 0x10


@packet(id=21)
class UpdateBlockPacket:
    """This happens often. Luckily, the packets are small."""

    pos: NetworkBlockPos = field(until=944)
    pos: BlockPos = field(since=944)
    runtime_id: BlockRuntimeId
    update_flags: uvarint32
    layer: uvarint32


@packet(id=134, since=361)
class UpdateBlockPropertiesPacket:
    properties: CompoundTag


# bedrock-headers declares
# `ActorBlockSyncMessage { ActorUniqueID mEntityUniqueID; MessageId mMessage; }`
# but the wire shape from CloudburstMC and gophertunnel encodes the entity id
# as uvarint64 (ActorRuntimeID), not the zigzag-signed varint64 that
# ActorUniqueID would use. Wire as ActorRuntimeID + uvarint64 MessageId.
class ActorBlockSyncMessage:
    # BDS: ActorBlockSyncMessage::MessageId (uint32_t, written as uvarint32).
    class MessageId(IntEnum):
        NONE = 0
        CREATE = 1
        DESTROY = 2

    entity_unique_id: ActorRuntimeID
    message: MessageId = field(type=uvarint64)


@packet(id=110)
class UpdateBlockSyncedPacket:
    """Variation of UpdateBlockPacket that includes information to sync entities with renderchunk
    generation. Occasionally when blocks change a sync message is sent and during the change on
    the dimension, this packet is sent to the client to alert the update flags and sync info at
    a specific position."""

    pos: NetworkBlockPos = field(until=944)
    pos: BlockPos = field(since=944)
    runtime_id: BlockRuntimeId
    update_flags: uvarint32
    layer: uvarint32
    entity_block_sync_message: ActorBlockSyncMessage


class UpdateSubChunkNetworkBlockInfo:
    pos: NetworkBlockPos = field(until=944)
    pos: BlockPos = field(since=944)
    runtime_id: uvarint32  # BlockRuntimeId
    update_flags: uvarint32  # BDS in-memory is `byte mUpdateFlags`; wire is uvarint32
    sync_message: ActorBlockSyncMessage


@packet(id=172, since=465)
class UpdateSubChunkBlocksPacket:
    """Packet sent for every set of blocks changed in a sub chunk every tick."""

    sub_chunk_block_position: NetworkBlockPos = field(until=944)
    sub_chunk_block_position: BlockPos = field(since=944)
    standards: list[UpdateSubChunkNetworkBlockInfo]
    extras: list[UpdateSubChunkNetworkBlockInfo]
