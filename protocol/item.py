from enum import IntEnum

from protocol import int16, packet
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


class ItemVersion(IntEnum):
    LEGACY = 0
    DATA_DRIVEN = 1
    NONE = 2


class ItemData:
    name: str
    id: int16
    is_component_based: bool
    item_version: ItemVersion
    component_data: CompoundTag


@packet(id=162)
class ItemRegistryPacket:
    items: list[ItemData]
