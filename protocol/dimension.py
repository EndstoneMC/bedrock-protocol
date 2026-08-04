import uuid

from protocol import field, packet, varint32
from protocol.attributes import DimensionType
from protocol.game import GeneratorType

package = "bedrock.protocol"


class DimensionDefinitionGroup:
    class DimensionDefinition:
        height_maximum: varint32
        height_minimum: varint32
        generator_type: GeneratorType
        dimension_type: DimensionType
        pack_id: uuid.UUID = field(since=2168)


@packet(id=180)
class DimensionDataPacket:
    dimension_definitions: dict[str, DimensionDefinitionGroup.DimensionDefinition]
