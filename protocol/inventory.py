from enum import IntEnum
from typing import Optional

from protocol import field, int8, int16, packet, type, uint8, uint16, uint32, uvarint32, varint32
from protocol.actor import ActorRuntimeID
from protocol.common import BlockPos, Vec3

package = "bedrock.protocol"

# ContainerID is signed-char in BDS (SharedTypes::Legacy::ContainerID).
type ContainerID = int8


class InventorySourceType(IntEnum, uint32):
    INVALID_INVENTORY = -1
    CONTAINER_INVENTORY = 0
    GLOBAL_INVENTORY = 1
    WORLD_INTERACTION = 2
    CREATIVE_INVENTORY = 3
    NON_IMPLEMENTED_FEATURE_TODO = 99999


class InventorySourceFlags(IntEnum, uint32):
    NO_FLAG = 0
    WORLD_INTERACTION_RANDOM = 1


class ContainerEnumName(IntEnum, uint8):
    ANVIL_INPUT_CONTAINER = 0
    ANVIL_MATERIAL_CONTAINER = 1
    ANVIL_RESULT_PREVIEW_CONTAINER = 2
    SMITHING_TABLE_INPUT_CONTAINER = 3
    SMITHING_TABLE_MATERIAL_CONTAINER = 4
    SMITHING_TABLE_RESULT_PREVIEW_CONTAINER = 5
    ARMOR_CONTAINER = 6
    LEVEL_ENTITY_CONTAINER = 7
    BEACON_PAYMENT_CONTAINER = 8
    BREWING_STAND_INPUT_CONTAINER = 9
    BREWING_STAND_RESULT_CONTAINER = 10
    BREWING_STAND_FUEL_CONTAINER = 11
    COMBINED_HOTBAR_AND_INVENTORY_CONTAINER = 12
    CRAFTING_INPUT_CONTAINER = 13
    CRAFTING_OUTPUT_PREVIEW_CONTAINER = 14
    RECIPE_CONSTRUCTION_CONTAINER = 15
    RECIPE_NATURE_CONTAINER = 16
    RECIPE_ITEMS_CONTAINER = 17
    RECIPE_SEARCH_CONTAINER = 18
    RECIPE_SEARCH_BAR_CONTAINER = 19
    RECIPE_EQUIPMENT_CONTAINER = 20
    RECIPE_BOOK_CONTAINER = 21
    ENCHANTING_INPUT_CONTAINER = 22
    ENCHANTING_MATERIAL_CONTAINER = 23
    FURNACE_FUEL_CONTAINER = 24
    FURNACE_INGREDIENT_CONTAINER = 25
    FURNACE_RESULT_CONTAINER = 26
    HORSE_EQUIP_CONTAINER = 27
    HOTBAR_CONTAINER = 28
    INVENTORY_CONTAINER = 29
    SHULKER_BOX_CONTAINER = 30
    TRADE_INGREDIENT_1_CONTAINER = 31
    TRADE_INGREDIENT_2_CONTAINER = 32
    TRADE_RESULT_PREVIEW_CONTAINER = 33
    OFFHAND_CONTAINER = 34
    COMPOUND_CREATOR_INPUT = 35
    COMPOUND_CREATOR_OUTPUT_PREVIEW = 36
    ELEMENT_CONSTRUCTOR_OUTPUT_PREVIEW = 37
    MATERIAL_REDUCER_INPUT = 38
    MATERIAL_REDUCER_OUTPUT = 39
    LAB_TABLE_INPUT = 40
    LOOM_INPUT_CONTAINER = 41
    LOOM_DYE_CONTAINER = 42
    LOOM_MATERIAL_CONTAINER = 43
    LOOM_RESULT_PREVIEW_CONTAINER = 44
    BLAST_FURNACE_INGREDIENT_CONTAINER = 45
    SMOKER_INGREDIENT_CONTAINER = 46
    TRADE2_INGREDIENT_1_CONTAINER = 47
    TRADE2_INGREDIENT_2_CONTAINER = 48
    TRADE2_RESULT_PREVIEW_CONTAINER = 49
    GRINDSTONE_INPUT_CONTAINER = 50
    GRINDSTONE_ADDITIONAL_CONTAINER = 51
    GRINDSTONE_RESULT_PREVIEW_CONTAINER = 52
    STONECUTTER_INPUT_CONTAINER = 53
    STONECUTTER_RESULT_PREVIEW_CONTAINER = 54
    CARTOGRAPHY_INPUT_CONTAINER = 55
    CARTOGRAPHY_ADDITIONAL_CONTAINER = 56
    CARTOGRAPHY_RESULT_PREVIEW_CONTAINER = 57
    BARREL_CONTAINER = 58
    CURSOR_CONTAINER = 59
    CREATED_OUTPUT_CONTAINER = 60
    SMITHING_TABLE_TEMPLATE_CONTAINER = 61
    CRAFTER_LEVEL_ENTITY_CONTAINER = 62
    DYNAMIC_CONTAINER = 63
    RECIPE_FOOD_CONTAINER = 64
    RECIPE_BLOCKS_CONTAINER = 65
    RECIPE_FURNACE_ITEMS_CONTAINER = 66


class ItemStackNetId:
    id: varint32


class ItemStackRequestId:
    id: varint32


class ItemStackLegacyRequestId:
    id: varint32


type ItemStackNetIdVariant = ItemStackNetId | ItemStackRequestId | ItemStackLegacyRequestId


@type(until=1001)
class SerializedNetworkItemStackDescriptor:
    """NetworkItemStackDescriptor::write. An air item (id 0) is a lone zero
    byte: the write returns early, so nothing else reaches the wire."""

    id: varint32

    with field(when=lambda d: d.id != 0):
        stack_size: uint16
        aux_value: uvarint32
        net_id: ItemStackNetId | None
        block_runtime_id: varint32
        user_data_buffer: bytes


@type(since=1001)
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


class LegacySetSlot:
    container_enum: ContainerEnumName
    slots: bytes


@type(until=1001)
class InventorySource:
    source_type: InventorySourceType
    container_id: ContainerID = field(
        type=varint32,
        when=lambda s: (
            s.source_type in {InventorySourceType.CONTAINER_INVENTORY, InventorySourceType.NON_IMPLEMENTED_FEATURE_TODO}
        ),
    )
    flags: InventorySourceFlags = field(when=lambda s: s.source_type == InventorySourceType.WORLD_INTERACTION)


# container_id and flags are cereal dynamic members: the composite-member loop
# writes an always-true member-present marker bool ahead of the value's own
# std::optional has-value bool -- two bools, but one std::optional in memory.
# The outer Optional models the marker; the inner is the real value.
@type(since=1001)
class InventorySource:
    source_type: InventorySourceType
    container_id: Optional[Optional[ContainerID]]
    flags: Optional[Optional[InventorySourceFlags]]


class InventoryAction:
    source: InventorySource
    slot: uvarint32
    from_item: SerializedNetworkItemStackDescriptor
    to_item: SerializedNetworkItemStackDescriptor


@type(until=1001)
class InventoryTransaction:
    actions: list[InventoryAction]


@type(since=1001)
class InventoryTransaction:
    actions: list[InventoryAction] | None


class NormalTransactionData:
    actions: InventoryTransaction


class InventoryMismatchData:
    actions: InventoryTransaction


class ItemUseInventoryTransactionActionType(IntEnum, uint32):
    PLACE = 0
    USE = 1
    DESTROY = 2
    USE_AS_ATTACK = 3


class ItemUseInventoryTransactionTriggerType(IntEnum, uint32):
    UNKNOWN = 0
    PLAYER_INPUT = 1
    SIMULATION_TICK = 2


class ItemUseInventoryTransactionPredictedResult(IntEnum, uint8):
    FAILURE = 0
    SUCCESS = 1


class ItemUseInventoryTransactionClientCooldownState(IntEnum, uint8):
    OFF = 0
    ON = 1


@type(until=1001)
class ItemUseInventoryTransaction:
    actions: InventoryTransaction
    action_type: ItemUseInventoryTransactionActionType
    trigger_type: ItemUseInventoryTransactionTriggerType
    pos: BlockPos
    face: varint32
    slot: varint32
    item: SerializedNetworkItemStackDescriptor
    from_pos: Vec3
    click_pos: Vec3
    target_block_id: uvarint32
    client_predicted_result: ItemUseInventoryTransactionPredictedResult = field(type=uvarint32)
    client_cooldown_state: ItemUseInventoryTransactionClientCooldownState


@type(since=1001)
class ItemUseInventoryTransaction:
    actions: InventoryTransaction
    action_type: ItemUseInventoryTransactionActionType
    trigger_type: ItemUseInventoryTransactionTriggerType
    pos: BlockPos
    face: uvarint32
    slot: varint32
    item: SerializedNetworkItemStackDescriptor
    from_pos: Vec3
    click_pos: Vec3
    target_block_id: uvarint32
    client_predicted_result: ItemUseInventoryTransactionPredictedResult
    client_cooldown_state: ItemUseInventoryTransactionClientCooldownState


class ItemUseOnActorInventoryTransactionActionType(IntEnum, uint32):
    INTERACT = 0
    ATTACK = 1


class ItemUseOnActorInventoryTransaction:
    actions: InventoryTransaction
    target_runtime_id: ActorRuntimeID
    action_type: ItemUseOnActorInventoryTransactionActionType
    slot: varint32
    item: SerializedNetworkItemStackDescriptor
    from_pos: Vec3
    hit_pos: Vec3


class ItemReleaseInventoryTransactionActionType(IntEnum, uint32):
    RELEASE = 0
    CONSUME = 1


class ItemReleaseInventoryTransaction:
    actions: InventoryTransaction
    action_type: ItemReleaseInventoryTransactionActionType
    slot: varint32
    item: SerializedNetworkItemStackDescriptor
    from_pos: Vec3


type TransactionData = (
    NormalTransactionData
    | InventoryMismatchData
    | ItemUseInventoryTransaction
    | ItemUseOnActorInventoryTransaction
    | ItemReleaseInventoryTransaction
)


@packet(id=30, until=1001)
class InventoryTransactionPacket:
    legacy_request_id: varint32
    legacy_set_item_slots: list[LegacySetSlot] = field(when=lambda p: p.legacy_request_id != 0)
    transaction: TransactionData


@packet(id=30, since=1001)
class InventoryTransactionPacket:
    legacy_request_id: varint32
    legacy_set_item_slots: list[LegacySetSlot] | None
    transaction: TransactionData | None
