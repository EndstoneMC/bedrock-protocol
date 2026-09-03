"""Dimension definitions and dimension change: world/level/dimension/.
Not DimensionType itself -- that is a versionless primitive, in common.py."""

import uuid

from protocol import field, packet, type, uint32, varint32
from protocol.common import DimensionType, Vec3
from protocol.game import GeneratorType

package = "bedrock.protocol"


class DimensionDefinitionGroup:
    @type(until=2192)
    class DimensionDefinition:
        height_maximum: varint32
        height_minimum: varint32
        generator_type: GeneratorType
        dimension_type: DimensionType
        pack_id: uuid.UUID = field(since=2168)

    @type(since=2192)
    class DimensionDefinition:
        minimum_y: varint32
        height_range: varint32
        generator_type: GeneratorType
        dimension_type: DimensionType
        pack_id: uuid.UUID
        default_biome: str


@packet(id=180)
class DimensionDataPacket:
    dimension_definitions: dict[str, DimensionDefinitionGroup.DimensionDefinition]


@packet(id=61, since=2168)
class ChangeDimensionPacket:
    dimension_id: DimensionType
    pos: Vec3
    respawn: bool
    loading_screen_id: uint32 | None
