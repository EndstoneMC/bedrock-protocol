"""The item as a subject: world/item/ -- the registry, the stack descriptors and the
net ids they carry, trims, cooldowns, book editing.
The net ids sit here rather than in item_stack.py because the descriptors reference them."""

from enum import IntEnum

from protocol import field, int16, int32, packet, type, uint8, uint16, uvarint32, varint32
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


@packet(id=176)
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


class BookEditAction(IntEnum, uint8):
    REPLACE_PAGE = 0
    ADD_PAGE = 1
    DELETE_PAGE = 2
    SWAP_PAGES = 3
    FINALIZE = 4


@packet(id=97, until=924)
class BookEditPacket:
    action: BookEditAction
    book_slot: int32 = field(type=uint8)
    page_index: int32 = field(type=uint8, when=lambda p: p.action != BookEditAction.FINALIZE)
    swap_with_index: int32 = field(type=uint8, when=lambda p: p.action == BookEditAction.SWAP_PAGES)

    with field(when=lambda p: p.action in {BookEditAction.REPLACE_PAGE, BookEditAction.ADD_PAGE}):
        page_text: str
        photo_name: str

    with field(when=lambda p: p.action == BookEditAction.FINALIZE):
        title: str
        author: str
        xuid: str


@packet(id=97, since=924)
class BookEditPacket:
    book_slot: varint32
    operation: ReplacePage | AddPage | DeletePage | SwapPages | Finalize


class TrimPattern:
    item_name: str
    pattern_id: str


class TrimMaterial:
    material_id: str
    color: str
    item_name: str


@packet(id=302)
class TrimDataPacket:
    trim_patterns: list[TrimPattern]
    trim_materials: list[TrimMaterial]


class ItemStackNetId:
    raw_id: varint32


class ItemStackRequestId:
    raw_id: varint32


class ItemStackLegacyRequestId:
    raw_id: varint32


type ItemStackNetIdVariant = ItemStackNetId | ItemStackRequestId | ItemStackLegacyRequestId


class NetworkItemStackDescriptor:
    """An air item (id 0) is a lone zero byte: the write returns early, so
    nothing else reaches the wire."""

    id: varint32

    with field(when=lambda d: d.id != 0):
        stack_size: uint16
        aux_value: uvarint32
        net_id: ItemStackNetId | None
        block_runtime_id: varint32
        user_data_buffer: bytes


@type(until=2168)
class SerializedNetworkItemStackDescriptor:
    """cerealizer<NetworkItemStackDescriptor>::SerializedData. The extra data
    (NBT, can-place-on / can-break, shield blocking tick) rides in a single
    length-prefixed blob, so it stays opaque here -- an empty blob is a lone
    uvarint32 zero, which is byte-identical to BDS's air-item early-out."""

    id: int16
    stack_size: uint16
    aux_value: uvarint32
    net_id_variant: ItemStackNetIdVariant | None
    block_runtime_id: uvarint32
    user_data_buffer: bytes


@type(since=2168)
class SerializedNetworkItemStackDescriptor:
    """cerealizer<NetworkItemStackDescriptor>::SerializedData. ItemStackNetIdVariant's
    binding projects its three alternatives onto one signed varint: non-negative
    is an ItemStackNetId, negative-odd an ItemStackRequestId, negative-even an
    ItemStackLegacyRequestId. The tag is gone, so the case is read back from the
    sign and parity."""

    id: int16
    stack_size: uint16
    aux_value: uvarint32
    net_id_variant: varint32 | None
    block_runtime_id: uvarint32
    user_data_buffer: bytes
