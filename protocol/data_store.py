"""The scripting data-store sync: scripting/data_sync/.
Name pinned: the DynamicValue builtin resolves include/bedrock/protocol/data_store.hpp
from this module's stem."""

from protocol import builtin, double, packet, type, uint32

package = "bedrock.protocol"


@builtin
class DynamicValue:
    """A recursive, self-describing data-store value: null, boolean, integer,
    number, string, array, or object (a string-keyed map of values)."""


@type(since=898, until=924)
class DataStoreUpdate:
    data_store_name: str
    property: str
    path: str
    data: double | bool | str
    update_count: uint32


@type(since=924)
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


@packet(id=330, since=859, until=898)
class DataStoreSyncPacket:
    updates: list[DataStoreChange | DataStoreRemoval]


@packet(id=330, since=898)
class ClientboundDataStorePacket:
    updates: list[DataStoreUpdate | DataStoreChange | DataStoreRemoval]


@packet(id=332, since=898)
class ServerboundDataStorePacket:
    update: DataStoreUpdate
