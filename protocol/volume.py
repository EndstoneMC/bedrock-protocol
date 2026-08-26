from protocol import packet, uvarint32
from protocol.attributes import DimensionType
from protocol.common import BlockPos
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


type EntityNetId = uvarint32


@packet(id=167, since=2168)
class RemoveVolumeEntityPacket:
    entity_net_id: EntityNetId
    dimension_type: DimensionType


@packet(id=166, since=2168)
class AddVolumeEntityPacket:
    entity_net_id: EntityNetId
    components: CompoundTag
    json_identifier: str
    instance_name: str
    min_bounds: BlockPos
    max_bounds: BlockPos
    dimension_type: DimensionType
    min_engine_version: str
