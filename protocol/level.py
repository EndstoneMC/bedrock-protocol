from protocol._dsl import field, packet
from protocol.common import BlockPos, varint32
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


class DimensionDefinition:
    name: str
    height_maximum: varint32
    height_minimum: varint32
    generator_type: varint32
    dimension_type: varint32 = field(since=975)


@packet(id=180, since=503)
class DimensionDataPacket:
    """Describes the data-driven dimensions a server has registered."""

    definitions: list[DimensionDefinition]


@packet(id=56, since=291)
class BlockActorDataPacket:
    """Updates the NBT data of the block entity at a position."""

    block_position: BlockPos
    actor_data_tags: CompoundTag
