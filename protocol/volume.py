from protocol import packet, uvarint32
from protocol.attributes import DimensionType

package = "bedrock.protocol"


type EntityNetId = uvarint32


@packet(id=167, since=2168)
class RemoveVolumeEntityPacket:
    entity_net_id: EntityNetId
    dimension_type: DimensionType
