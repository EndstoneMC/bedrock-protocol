"""Containers and inventory options: world/containers/ + world/inventory/ --
container ids and types, screen options, furnace, stonecutter and trade windows, equipment.
Not the item-stack request/response protocol -- world/inventory/network/, in item_stack.py.
Not the legacy transaction family -- world/inventory/transaction/, in transaction.py."""

from enum import IntEnum, auto

from protocol import field, int8, int16, int32, packet, type, uint8, uint32, uvarint32, value, varint32
from protocol.actor import ActorRuntimeID, ActorUniqueID
from protocol.common import BlockPos
from protocol.item import NetworkItemStackDescriptor, SerializedNetworkItemStackDescriptor
from protocol.nbt import CompoundTag
from protocol.network import NetworkBlockPosition

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"


class ContainerID(IntEnum, int8):
    NONE = -1, "CONTAINER_ID_NONE"
    INVENTORY = 0, "CONTAINER_ID_INVENTORY"
    FIRST = 1, "CONTAINER_ID_FIRST"
    LAST = 100, "CONTAINER_ID_LAST"
    OFFHAND = 119, "CONTAINER_ID_OFFHAND"
    ARMOR = 120, "CONTAINER_ID_ARMOR"
    SELECTION_SLOTS = 122, "CONTAINER_ID_SELECTION_SLOTS"
    PLAYER_ONLY_UI = 124, "CONTAINER_ID_PLAYER_ONLY_UI"
    REGISTRY = 125, "CONTAINER_ID_REGISTRY"
    REGISTRY_INVENTORY = value(126, until=748)


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
    with value(since=924):
        RECIPE_FOOD_CONTAINER = 64
        RECIPE_BLOCKS_CONTAINER = 65
        RECIPE_FURNACE_ITEMS_CONTAINER = 66
    with value(since=2225):
        DISC_PRESS_BLOCK_CONTAINER = 67
        DISC_PRESS_DYE_CONTAINER = 68
        DISC_PRESS_DISC_CONTAINER = 69
        DISC_PRESS_RESULT_PREVIEW_CONTAINER = 70


class FullContainerName:
    name: ContainerEnumName
    dynamic_id: uint32 | None


@packet(id=49, until=1001)
class InventoryContentPacket:
    inventory_id: ContainerID = field(type=uvarint32)
    slots: list[NetworkItemStackDescriptor]
    full_container_name: FullContainerName
    dynamic_container_size: uvarint32 = field(until=748)
    storage_item: NetworkItemStackDescriptor = field(since=748)


@packet(id=49, since=1001)
class InventoryContentPacket:
    inventory_id: ContainerID = field(type=uvarint32)
    slots: list[SerializedNetworkItemStackDescriptor]
    full_container_name: FullContainerName
    storage_item: SerializedNetworkItemStackDescriptor


@packet(id=50, until=975)
class InventorySlotPacket:
    inventory_id: ContainerID = field(type=uvarint32)
    slot: uvarint32
    full_container_name: FullContainerName
    dynamic_container_size: uvarint32 = field(until=748)
    storage_item: NetworkItemStackDescriptor = field(since=748)
    item: NetworkItemStackDescriptor


@packet(id=50, since=975)
class InventorySlotPacket:
    inventory_id: ContainerID = field(type=uint8)
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
    BREWING_STAND = 4, "BREWING_STAND"
    ANVIL = 5
    DISPENSER = 6
    DROPPER = 7
    HOPPER = 8
    CAULDRON = 9
    MINECART_CHEST = 10, "MINECART_CHEST"
    MINECART_HOPPER = 11, "MINECART_HOPPER"
    HORSE = 12
    BEACON = 13
    STRUCTURE_EDITOR = 14, "STRUCTURE_EDITOR"
    TRADE = 15
    COMMAND_BLOCK = 16, "COMMAND_BLOCK"
    JUKEBOX = 17
    ARMOR = 18
    HAND = 19
    COMPOUND_CREATOR = 20, "COMPOUND_CREATOR"
    ELEMENT_CONSTRUCTOR = 21, "ELEMENT_CONSTRUCTOR"
    MATERIAL_REDUCER = 22, "MATERIAL_REDUCER"
    LAB_TABLE = 23, "LAB_TABLE"
    LOOM = 24
    LECTERN = 25
    GRINDSTONE = 26
    BLAST_FURNACE = 27, "BLAST_FURNACE"
    SMOKER = 28
    STONECUTTER = 29
    CARTOGRAPHY = 30
    HUD = 31
    JIGSAW_EDITOR = 32, "JIGSAW_EDITOR"
    SMITHING_TABLE = 33, "SMITHING_TABLE"
    CHEST_BOAT = 34, "CHEST_BOAT"
    DECORATED_POT = 35, "DECORATED_POT"
    CRAFTER = 36
    DATA_DRIVEN_CONTAINER = value(37, "DATA_DRIVEN_CONTAINER", since=2193)
    DISC_PRESS = value(38, "DISC_PRESS", since=2225)


@packet(id=47)
class ContainerClosePacket:
    container_id: ContainerID = field(type=uint8)
    container_type: ContainerType
    server_initiated_close: bool


@packet(id=48)
class PlayerHotbarPacket:
    selected_slot: uvarint32
    container_id: ContainerID = field(type=uint8)
    should_select_slot: bool


@packet(id=51)
class ContainerSetDataPacket:
    container_id: ContainerID = field(type=uint8)
    id: varint32
    value: varint32


@packet(id=54)
class GuiDataPickItemPacket:
    item_name: str
    item_effect_name: str
    slot: int32


@packet(id=142)
class CompletedUsingItemPacket:
    item_id: int16
    item_use_method: int32


@packet(id=306)
class PlayerToggleCrafterSlotRequestPacket:
    pos_x: int32
    pos_y: int32
    pos_z: int32
    slot_index: int32 = field(type=uint8)
    is_disabled: bool


@packet(id=46)
class ContainerOpenPacket:
    container_id: ContainerID = field(type=uint8)
    type: ContainerType
    pos: NetworkBlockPosition = field(until=944)
    pos: BlockPos = field(since=944)
    entity_unique_id: ActorUniqueID


@packet(id=317)
class ContainerRegistryCleanupPacket:
    removed_containers: list[FullContainerName]


class InventoryLayout(IntEnum, int32):
    NONE = 0
    INVENTORY_ONLY = 1
    DEFAULT = 2
    RECIPE_BOOK_ONLY = 3
    COUNT = auto()


class InventoryLeftTabIndex(IntEnum, int32):
    NONE = 0
    RECIPE_CONSTRUCTION = 1
    RECIPE_EQUIPMENT = 2
    RECIPE_ITEMS = 3
    RECIPE_NATURE = 4
    RECIPE_SEARCH = 5
    SURVIVAL = 6
    COUNT = auto()


class InventoryRightTabIndex(IntEnum, int32):
    NONE = 0
    FULL_SCREEN = 1
    CRAFTING = 2
    ARMOR = 3
    COUNT = auto()


class InventoryOptions:
    left_inventory_tab: InventoryLeftTabIndex
    right_inventory_tab: InventoryRightTabIndex
    filtering: bool
    layout_inv: InventoryLayout
    layout_craft: InventoryLayout


@packet(id=307)
class SetPlayerInventoryOptionsPacket:
    inventory_options: InventoryOptions


class FurnaceLeftTabIndex(IntEnum, int32):
    NONE = 0
    RECIPE_FOOD = 1
    RECIPE_ITEMS = 2
    RECIPE_BLOCKS = 3
    RECIPE_SEARCH = 4
    INVENTORY = 5
    COUNT = auto()


class FurnaceLayout(IntEnum, int32):
    NONE = 0
    INVENTORY_ONLY = 1
    DEFAULT = 2
    COUNT = auto()


class FurnaceOptions:
    left_furnace_tab: FurnaceLeftTabIndex
    filtering: bool
    layout: FurnaceLayout


@packet(id=351, since=2193)
class SetPlayerFurnaceOptionsPacket:
    class FurnaceType(IntEnum, uint8):
        NONE = 0
        FURNACE = 1
        BLAST_FURNACE = 2
        SMOKER = 3
        COUNT = auto()

    furnace_type: FurnaceType
    furnace_options: FurnaceOptions


@packet(id=354, since=2225)
class ServerboundStonecutterSetRecipePacket:
    container_id: ContainerID = field(type=uint8)
    recipe_index: varint32


@packet(id=355, since=2225)
class ClientboundStonecutterSetRecipePacket:
    player_unique_id: ActorUniqueID
    container_id: ContainerID = field(type=uint8)
    recipe_index: varint32


@type(since=2225)
class CursorItemDragState(IntEnum, uint8):
    START = 0
    STOP = 1


@packet(id=358, since=2225)
class ServerboundCursorItemDragPacket:
    state: CursorItemDragState


@packet(id=80)
class UpdateTradePacket:
    container_id: ContainerID = field(type=uint8)
    type: ContainerType
    size: varint32
    trader_tier: varint32
    entity_unique_id: ActorUniqueID
    last_trading_player: ActorUniqueID
    display_name: str
    use_new_trade_screen: bool
    using_economy_trade: bool
    data: CompoundTag


@packet(id=81)
class UpdateEquipPacket:
    container_id: ContainerID = field(type=uint8)
    type: ContainerType
    size: varint32
    entity_unique_id: ActorUniqueID
    data: CompoundTag


@packet(id=31)
class MobEquipmentPacket:
    runtime_id: ActorRuntimeID
    item: NetworkItemStackDescriptor = field(until=975)
    item: SerializedNetworkItemStackDescriptor = field(since=975)
    slot: int32 = field(type=uint8)
    selected_slot: int32 = field(type=uint8)
    container_id: ContainerID = field(type=uint8)


@packet(id=32, until=1001)
class MobArmorEquipmentPacket:
    runtime_id: ActorRuntimeID
    head: NetworkItemStackDescriptor
    torso: NetworkItemStackDescriptor
    legs: NetworkItemStackDescriptor
    feet: NetworkItemStackDescriptor
    body: NetworkItemStackDescriptor


@packet(id=32, since=1001)
class MobArmorEquipmentPacket:
    runtime_id: ActorRuntimeID
    head: SerializedNetworkItemStackDescriptor
    torso: SerializedNetworkItemStackDescriptor
    legs: SerializedNetworkItemStackDescriptor
    feet: SerializedNetworkItemStackDescriptor
    body: SerializedNetworkItemStackDescriptor
