from protocol import double, packet, uint32

package = "bedrock.protocol"


class DataStoreUpdate:
    data_store_name: str
    property: str
    path: str
    data: double | bool | str
    property_update_count: uint32
    path_update_count: uint32


@packet(id=332, since=2168)
class ServerboundDataStorePacket:
    update: DataStoreUpdate
