from protocol import packet, uint8, uint16, uvarint32
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


type RegistryHandle = uint16


class SerializableCells:
    x_size: uint8
    y_size: uint8
    z_size: uint8
    storage: list[uint8]


class SerializableVoxelShape:
    cells: SerializableCells
    x_coords: list[float]
    y_coords: list[float]
    z_coords: list[float]


@packet(id=337, since=2168)
class VoxelShapesPacket:
    shapes: list[SerializableVoxelShape]
    name_map: dict[str, RegistryHandle]
    custom_shape_count: uint16
