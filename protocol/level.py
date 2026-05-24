from protocol import field, int8, int64, packet, type, uint32, uint64, uvarint32, varint32
from protocol.common import BlockPos, SubChunkPos, Vec3
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


@type(since=975)
class ServerSoundHandle:
    value: uint64


@packet(id=86)
class PlaySoundPacket:
    name: str
    pos: BlockPos
    volume: float
    pitch: float
    server_sound_handle: ServerSoundHandle | None = field(since=975)


@packet(id=123, since=332)
class LevelSoundEventPacket:
    """Most sounds get launched on server and replicated to clients, but a handful of player
    initiated sounds are launched on their client and replicated through the network."""

    event_id: uvarint32
    pos: Vec3
    data: varint32
    actor_identifier: str
    is_baby: bool
    is_global: bool
    actor: int64 = field(since=786)
    fire_at_position: Vec3 | None = field(since=975)


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
