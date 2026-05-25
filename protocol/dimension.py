from enum import IntEnum

from protocol import (
    field,
    packet,
    uint32,
    varint32,
)
from protocol.common import Vec3

package = "bedrock.protocol"

type DimensionType = varint32


class GeneratorType(IntEnum):
    LEGACY = 0
    OVERWORLD = 1
    FLAT = 2
    NETHER = 3
    THE_END = 4
    VOID = 5
    UNDEFINED = 6


@packet(id=61)
class ChangeDimensionPacket:
    """The server sends this packet from the level to kick off dimension changing process."""

    dimension_id: DimensionType
    pos: Vec3
    respawn: bool
    loading_screen_id: uint32 | None = field(since=712)


class DimensionDefinition:
    """Member of DimensionDefinitionGroup; mirrors BDS DimensionDefinitionGroup::DimensionDefinition."""

    id: str
    height_maximum: varint32
    height_minimum: varint32
    generator_type: GeneratorType = field(type=varint32)
    dimension_type: DimensionType = field(type=varint32, since=975)


@packet(id=180, since=503)
class DimensionDataPacket:
    """Sends a DimensionDefinitionGroup to the client so the client knows how each dimension is
    configured (height range, generator, dimension type)."""

    dimension_definitions: list[DimensionDefinition]
