from enum import IntEnum

from protocol import int16, packet, varint32
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


@packet(id=176, since=2168)
class PlayerStartItemCooldownPacket:
    item_category: str
    duration_ticks: varint32


class ReplacePage:
    page_index: varint32
    page_text: str
    photo_name: str


class AddPage:
    page_index: varint32
    page_text: str
    photo_name: str


class DeletePage:
    page_index: varint32


class SwapPages:
    page_index: varint32
    swap_with_index: varint32


class Finalize:
    title: str
    author: str
    xuid: str


@packet(id=97, since=2168)
class BookEditPacket:
    book_slot: varint32
    operation: ReplacePage | AddPage | DeletePage | SwapPages | Finalize
