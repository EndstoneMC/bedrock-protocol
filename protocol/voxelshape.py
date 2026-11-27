"""Packets and types relating to voxel shapes."""

from protocol import field, packet, uint8, uint16

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"
go_package = "github.com/EndstoneMC/bedrock-protocol/go/protocol"


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


@packet(id=337, since=924)
class VoxelShapesPacket:
    shapes: list[SerializableVoxelShape]
    name_map: dict[str, RegistryHandle]
    custom_shape_count: uint16 = field(since=944)
