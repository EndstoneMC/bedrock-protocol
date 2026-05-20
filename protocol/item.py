from protocol import field, int16, uint16, uvarint32, varint32

package = "bedrock.protocol"


class NetworkItemStackDescriptor:
    id: varint32
    with field(when=lambda p: p.id != 0):
        count: uint16
        aux_value: uvarint32
        net_id: varint32 | None
        block_runtime_id: varint32
        user_data: bytes


class NetworkItemInstanceDescriptor:
    id: varint32
    with field(when=lambda p: p.id != 0):
        count: uint16
        aux_value: uvarint32
        block_runtime_id: varint32
        user_data: bytes


class ItemStackServerNetId:
    id: varint32


class ItemStackRequestId:
    id: varint32


class ItemStackLegacyRequestId:
    id: varint32


type ItemStackNetIdVariant = (
    ItemStackServerNetId | ItemStackRequestId | ItemStackLegacyRequestId
)


class SerializedNetworkItemStackDescriptor:
    """Mirror of the BDS type cerealizer<NetworkItemStackDescriptor>::SerializedData."""

    id: int16
    count: uint16
    aux_value: uvarint32
    net_id: ItemStackNetIdVariant | None
    block_runtime_id: uvarint32
    user_data: bytes
