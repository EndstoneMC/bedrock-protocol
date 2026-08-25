from enum import IntEnum, auto
from typing import Literal

from protocol import field, int8, int16, packet, type, uint8, uint16, uint32, uvarint32, varint32
from protocol.actor import ActorRuntimeID
from protocol.common import BlockPos, Vec3

package = "bedrock.protocol"


class ContainerID(IntEnum, int8):
    NONE = -1
    INVENTORY = 0
    FIRST = 1
    LAST = 100
    OFFHAND = 119
    ARMOR = 120
    SELECTION_SLOTS = 122
    PLAYER_ONLY_UI = 124
    REGISTRY = 125


class InventorySourceType(IntEnum, uint32):
    INVALID_INVENTORY = -1
    CONTAINER_INVENTORY = 0
    GLOBAL_INVENTORY = 1
    WORLD_INTERACTION = 2
    CREATIVE_INVENTORY = 3
    NON_IMPLEMENTED_FEATURE_TODO = 99999


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


class HandSlot(IntEnum, uint8):
    MAINHAND = 0
    OFFHAND = 1
    COUNT = auto()


class FullContainerName:
    name: ContainerEnumName
    dynamic_id: uint32 | None


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


class LegacySetSlot:
    container_enum: ContainerEnumName
    slots: bytes


@type(until=1001)
class InventorySource:
    class InventorySourceFlags(IntEnum, uint32):
        NO_FLAG = 0
        WORLD_INTERACTION_RANDOM = 1

    type: InventorySourceType
    container_id: ContainerID = field(
        type=varint32,
        when=lambda s: (
            s.type in {InventorySourceType.CONTAINER_INVENTORY, InventorySourceType.NON_IMPLEMENTED_FEATURE_TODO}
        ),
    )
    flags: InventorySourceFlags = field(when=lambda s: s.type == InventorySourceType.WORLD_INTERACTION)


@type(since=1001)
class InventorySource:
    class InventorySourceFlags(IntEnum, uint32):
        NO_FLAG = 0
        WORLD_INTERACTION_RANDOM = 1

    type: InventorySourceType
    _true_1: Literal[True] = field(until=2192)  # blameMojang: why, uhhh?
    container_id: ContainerID | None
    _true_2: Literal[True] = field(until=2192)  # blameMojang: hello?
    flags: InventorySourceFlags | None


@type(until=1001)
class InventoryAction:
    source: InventorySource
    slot: uvarint32
    from_item_descriptor: NetworkItemStackDescriptor
    to_item_descriptor: NetworkItemStackDescriptor


@type(since=1001)
class InventoryAction:
    source: InventorySource
    slot: uvarint32
    from_item_descriptor: SerializedNetworkItemStackDescriptor
    to_item_descriptor: SerializedNetworkItemStackDescriptor


@type(until=1001)
class InventoryTransaction:
    actions: list[InventoryAction]


@type(since=1001)
class InventoryTransaction:
    _true: Literal[True] = field(until=2192)
    actions: list[InventoryAction]


class NormalTransactionData:
    transaction: InventoryTransaction


class InventoryMismatchData:
    transaction: InventoryTransaction


@type(until=1001)
class ItemUseInventoryTransaction:
    class ActionType(IntEnum):
        PLACE = 0
        USE = 1
        DESTROY = 2
        USE_AS_ATTACK = 3

    class TriggerType(IntEnum, uint8):
        UNKNOWN = 0
        PLAYER_INPUT = 1
        SIMULATION_TICK = 2

    class PredictedResult(IntEnum, uint8):
        FAILURE = 0
        SUCCESS = 1

    class ClientCooldownState(IntEnum, uint8):
        OFF = 0
        ON = 1

    transaction: InventoryTransaction
    action_type: ActionType = field(type=uvarint32)
    trigger_type: TriggerType
    pos: BlockPos
    face: varint32
    slot: varint32
    item: NetworkItemStackDescriptor
    from_pos: Vec3
    click_pos: Vec3
    target_block_id: uvarint32
    client_predicted_result: PredictedResult = field(type=uvarint32)
    client_cooldown_state: ClientCooldownState


@type(since=1001)
class ItemUseInventoryTransaction:
    class ActionType(IntEnum):
        PLACE = 0
        USE = 1
        DESTROY = 2
        USE_AS_ATTACK = 3

    class TriggerType(IntEnum, uint8):
        UNKNOWN = 0
        PLAYER_INPUT = 1
        SIMULATION_TICK = 2

    class PredictedResult(IntEnum, uint8):
        FAILURE = 0
        SUCCESS = 1

    class ClientCooldownState(IntEnum, uint8):
        OFF = 0
        ON = 1

    transaction: InventoryTransaction
    action_type: ActionType
    trigger_type: TriggerType
    pos: BlockPos
    face: uint8
    slot: varint32
    hand: HandSlot = field(since=2192)
    item: SerializedNetworkItemStackDescriptor
    from_pos: Vec3
    click_pos: Vec3
    target_block_id: uvarint32
    client_predicted_result: PredictedResult
    client_cooldown_state: ClientCooldownState


@type(cereal=False, until=1001)
class ItemUseInventoryTransaction:
    """The shape PlayerAuthInputPacket writes: that packet did not cerealise until
    2168, so its transaction keeps the pre-cereal framing -- the action list carries
    no member-present marker and `face` stays a varint32 -- while its leaves
    cerealise at 1001 with everything else."""

    actions: list[InventoryAction]
    action_type: ItemUseInventoryTransaction.ActionType = field(type=uvarint32)
    trigger_type: ItemUseInventoryTransaction.TriggerType
    pos: BlockPos
    face: varint32
    slot: varint32
    item: NetworkItemStackDescriptor
    from_pos: Vec3
    click_pos: Vec3
    target_block_id: uvarint32
    client_predicted_result: ItemUseInventoryTransaction.PredictedResult = field(type=uvarint32)
    client_cooldown_state: ItemUseInventoryTransaction.ClientCooldownState


@type(cereal=False, since=1001)
class ItemUseInventoryTransaction:
    actions: list[InventoryAction]
    action_type: ItemUseInventoryTransaction.ActionType = field(type=uvarint32)
    trigger_type: ItemUseInventoryTransaction.TriggerType
    pos: BlockPos
    face: varint32
    slot: varint32
    item: SerializedNetworkItemStackDescriptor
    from_pos: Vec3
    click_pos: Vec3
    target_block_id: uvarint32
    client_predicted_result: ItemUseInventoryTransaction.PredictedResult
    client_cooldown_state: ItemUseInventoryTransaction.ClientCooldownState


@type(until=1001)
class ItemUseOnActorInventoryTransaction:
    class ActionType(IntEnum):
        INTERACT = 0
        ATTACK = 1
        ITEM_INTERACT = 2

    transaction: InventoryTransaction
    runtime_id: ActorRuntimeID
    action_type: ActionType = field(type=uvarint32)
    slot: varint32
    item: NetworkItemStackDescriptor
    from_pos: Vec3
    hit_pos: Vec3


@type(since=1001)
class ItemUseOnActorInventoryTransaction:
    class ActionType(IntEnum):
        INTERACT = 0
        ATTACK = 1
        ITEM_INTERACT = 2

    transaction: InventoryTransaction
    runtime_id: ActorRuntimeID
    action_type: ActionType
    slot: varint32
    item: SerializedNetworkItemStackDescriptor
    from_pos: Vec3
    hit_pos: Vec3


@type(until=1001)
class ItemReleaseInventoryTransaction:
    class ActionType(IntEnum):
        RELEASE = 0
        USE = 1

    transaction: InventoryTransaction
    action_type: ActionType = field(type=uvarint32)
    slot: varint32
    item: NetworkItemStackDescriptor
    from_pos: Vec3


@type(since=1001)
class ItemReleaseInventoryTransaction:
    class ActionType(IntEnum):
        RELEASE = 0
        USE = 1

    transaction: InventoryTransaction
    action_type: ActionType
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
    _true: Literal[True] = field(until=2192)
    transaction: TransactionData


@packet(id=49, until=1001)
class InventoryContentPacket:
    inventory_id: ContainerID = field(type=uvarint32)
    slots: list[NetworkItemStackDescriptor]
    full_container_name: FullContainerName
    storage_item: NetworkItemStackDescriptor


@packet(id=49, since=1001)
class InventoryContentPacket:
    inventory_id: ContainerID = field(type=uvarint32)
    slots: list[SerializedNetworkItemStackDescriptor]
    full_container_name: FullContainerName
    storage_item: SerializedNetworkItemStackDescriptor


@packet(id=50)
class InventorySlotPacket:
    inventory_id: ContainerID
    slot: uvarint32
    full_container_name: FullContainerName | None
    storage_item: SerializedNetworkItemStackDescriptor | None
    item: SerializedNetworkItemStackDescriptor


class ContainerType(IntEnum, int8):
    NONE = -9
    INVENTORY = -1
    CONTAINER = 0
    WORKBENCH = 1
    FURNACE = 2
    ENCHANTMENT = 3
    BREWING_STAND = 4
    ANVIL = 5
    DISPENSER = 6
    DROPPER = 7
    HOPPER = 8
    CAULDRON = 9
    MINECART_CHEST = 10
    MINECART_HOPPER = 11
    HORSE = 12
    BEACON = 13
    STRUCTURE_EDITOR = 14
    TRADE = 15
    COMMAND_BLOCK = 16
    JUKEBOX = 17
    ARMOR = 18
    HAND = 19
    COMPOUND_CREATOR = 20
    ELEMENT_CONSTRUCTOR = 21
    MATERIAL_REDUCER = 22
    LAB_TABLE = 23
    LOOM = 24
    LECTERN = 25
    GRINDSTONE = 26
    BLAST_FURNACE = 27
    SMOKER = 28
    STONECUTTER = 29
    CARTOGRAPHY = 30
    HUD = 31
    JIGSAW_EDITOR = 32
    SMITHING_TABLE = 33
    CHEST_BOAT = 34
    DECORATED_POT = 35
    CRAFTER = 36


@packet(id=47, since=2168)
class ContainerClosePacket:
    container_id: ContainerID
    container_type: ContainerType
    server_initiated_close: bool


@packet(id=48, since=2168)
class PlayerHotbarPacket:
    selected_slot: uvarint32
    container_id: ContainerID
    should_select_slot: bool
