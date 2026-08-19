import uuid

from protocol import field, packet, type, varint32
from protocol.attributes import DimensionType
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
        # BDS renamed both leading members at 2192, and they do not name what they used to:
        # the pair went from a maximum and a minimum to a floor and the span above it.
        minimum_y: varint32
        height_range: varint32
        generator_type: GeneratorType
        dimension_type: DimensionType
        pack_id: uuid.UUID
        default_biome: str


@packet(id=180)
class DimensionDataPacket:
    dimension_definitions: dict[str, DimensionDefinitionGroup.DimensionDefinition]
