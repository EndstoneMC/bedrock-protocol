"""The scripting data-store sync: scripting/data_sync/.
Name pinned: the DynamicValue builtin resolves include/bedrock/protocol/data_store.hpp
from this module's stem."""

from protocol import builtin, double, packet, uint32

package = "bedrock.protocol"


@builtin
class DynamicValue:
    """A recursive, self-describing data-store value: null, boolean, integer,
    number, string, array, or object (a string-keyed map of values)."""


class DataStoreUpdate:
    data_store_name: str
    property: str
    path: str
    data: double | bool | str
    property_update_count: uint32
    path_update_count: uint32


class DataStoreChange:
    data_store_name: str
    property: str
    update_count: uint32
    new_data: DynamicValue


class DataStoreRemoval:
    data_store_name: str


@packet(id=330)
class ClientboundDataStorePacket:
    updates: list[DataStoreUpdate | DataStoreChange | DataStoreRemoval]


@packet(id=332)
class ServerboundDataStorePacket:
    update: DataStoreUpdate
