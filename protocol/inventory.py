from enum import IntEnum

from protocol import field, int16, int32, uint8, uint16, uint32, uvarint32, varint32
from protocol.common import BlockPos, Vec3

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


class ContainerEnumName(IntEnum):
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


class InventorySourceType(IntEnum):
    CONTAINER_INVENTORY = 0
    GLOBAL_INVENTORY = 1
    WORLD_INTERACTION = 2
    CREATIVE_INVENTORY = 3
    NON_IMPLEMENTED_FEATURE_TODO = 99999


class InventorySource:
    source_type: InventorySourceType = field(type=uvarint32)
    container_id: varint32 = field(
        when=lambda p: (
            p.source_type == InventorySourceType.CONTAINER_INVENTORY
            or p.source_type == InventorySourceType.NON_IMPLEMENTED_FEATURE_TODO
        ),
    )
    flags: uvarint32 = field(
        when=lambda p: p.source_type == InventorySourceType.WORLD_INTERACTION,
    )


class InventoryAction:
    source: InventorySource
    slot: uvarint32
    from_item: NetworkItemStackDescriptor
    to_item: NetworkItemStackDescriptor


class InventoryTransaction:
    actions: list[InventoryAction]


class LegacySetItemSlot:
    container_enum_name: ContainerEnumName = field(type=uint8)
    slots: bytes


class ItemUseInventoryTransaction:
    class ActionType(IntEnum):
        PLACE = 0
        USE = 1
        DESTROY = 2
        USE_AS_ATTACK = 3

    class TriggerType(IntEnum):
        UNKNOWN = 0
        PLAYER_INPUT = 1
        SIMULATION_TICK = 2

    class PredictedResult(IntEnum):
        FAILURE = 0
        SUCCESS = 1

    class ClientCooldownState(IntEnum):
        OFF = 0
        ON = 1

    transaction: InventoryTransaction
    action_type: ActionType = field(type=uvarint32)
    trigger_type: TriggerType = field(type=uvarint32, since=712)
    position: BlockPos
    face: varint32
    slot: varint32
    item: NetworkItemStackDescriptor
    from_position: Vec3
    click_position: Vec3
    target_block_id: uvarint32
    client_interact_prediction: PredictedResult = field(type=uint8, since=712)
    client_cooldown_state: ClientCooldownState = field(type=uint8, since=944)


class PackedItemUseLegacyInventoryTransaction:
    id: ItemStackLegacyRequestId
    container_slots: list[LegacySetItemSlot] = field(
        when=lambda p: p.id.id < -1 and (p.id.id & 1) == 0,
    )
    transaction: ItemUseInventoryTransaction


class FullContainerName:
    container_name: ContainerEnumName = field(type=uint8)
    dynamic_id: uint32 | None


class ItemStackRequestSlotInfo:
    container: FullContainerName
    slot: uint8
    stack_network_id: varint32


class InvalidItemDescriptor:
    pass


class InternalItemDescriptor:
    network_id: int16
    metadata_value: int16 = field(when=lambda p: p.network_id != 0)


class MolangItemDescriptor:
    expression: str
    version: uint8


class ItemTagItemDescriptor:
    tag: str


class DeferredItemDescriptor:
    name: str
    metadata_value: int16


class ComplexAliasItemDescriptor:
    name: str


type ItemDescriptor = (
    InvalidItemDescriptor
    | InternalItemDescriptor
    | MolangItemDescriptor
    | ItemTagItemDescriptor
    | DeferredItemDescriptor
    | ComplexAliasItemDescriptor
)


class ItemDescriptorCount:
    descriptor: ItemDescriptor
    count: varint32


class TakeStackRequestAction:
    count: uint8
    source: ItemStackRequestSlotInfo
    destination: ItemStackRequestSlotInfo


class PlaceStackRequestAction:
    count: uint8
    source: ItemStackRequestSlotInfo
    destination: ItemStackRequestSlotInfo


class SwapStackRequestAction:
    source: ItemStackRequestSlotInfo
    destination: ItemStackRequestSlotInfo


class DropStackRequestAction:
    count: uint8
    source: ItemStackRequestSlotInfo
    randomly: bool


class DestroyStackRequestAction:
    count: uint8
    source: ItemStackRequestSlotInfo


class ConsumeStackRequestAction:
    count: uint8
    source: ItemStackRequestSlotInfo


class CreateStackRequestAction:
    results_slot: uint8


class PlaceInItemContainerDeprecatedStackRequestAction:
    count: uint8
    source: ItemStackRequestSlotInfo
    destination: ItemStackRequestSlotInfo


class TakeFromItemContainerDeprecatedStackRequestAction:
    count: uint8
    source: ItemStackRequestSlotInfo
    destination: ItemStackRequestSlotInfo


class ScreenLabTableCombineStackRequestAction:
    pass


class ScreenBeaconPaymentStackRequestAction:
    primary_effect: varint32
    secondary_effect: varint32


class ScreenHUDMineBlockStackRequestAction:
    hotbar_slot: varint32
    predicted_durability: varint32
    stack_network_id: varint32


class CraftRecipeStackRequestAction:
    recipe_network_id: uvarint32
    num_crafts: uint8


class CraftRecipeAutoStackRequestAction:
    recipe_network_id: uvarint32
    num_requested_crafts: uint8
    num_crafts: uint8
    ingredients: list[ItemDescriptorCount]


class CraftCreativeStackRequestAction:
    creative_item_network_id: uvarint32
    num_crafts: uint8


class CraftRecipeOptionalStackRequestAction:
    recipe_network_id: uvarint32
    filter_string_index: int32


class CraftRepairAndDisenchantStackRequestAction:
    recipe_network_id: uvarint32
    num_crafts: uint8
    cost: varint32


class CraftLoomStackRequestAction:
    pattern: str
    times_crafted: uint8


class CraftNonImplementedDeprecatedStackRequestAction:
    pass


class CraftResultsDeprecatedStackRequestAction:
    result_items: list[NetworkItemInstanceDescriptor]
    times_crafted: uint8


type ItemStackRequestAction = (
    TakeStackRequestAction
    | PlaceStackRequestAction
    | SwapStackRequestAction
    | DropStackRequestAction
    | DestroyStackRequestAction
    | ConsumeStackRequestAction
    | CreateStackRequestAction
    | PlaceInItemContainerDeprecatedStackRequestAction
    | TakeFromItemContainerDeprecatedStackRequestAction
    | ScreenLabTableCombineStackRequestAction
    | ScreenBeaconPaymentStackRequestAction
    | ScreenHUDMineBlockStackRequestAction
    | CraftRecipeStackRequestAction
    | CraftRecipeAutoStackRequestAction
    | CraftCreativeStackRequestAction
    | CraftRecipeOptionalStackRequestAction
    | CraftRepairAndDisenchantStackRequestAction
    | CraftLoomStackRequestAction
    | CraftNonImplementedDeprecatedStackRequestAction
    | CraftResultsDeprecatedStackRequestAction
)


class TextProcessingEventOrigin(IntEnum):
    SERVER_CHAT_PUBLIC = 0
    SERVER_CHAT_WHISPER = 1
    SIGN_TEXT = 2
    ANVIL_TEXT = 3
    BOOK_AND_QUILL_TEXT = 4
    COMMAND_BLOCK_TEXT = 5
    BLOCK_ACTOR_DATA_TEXT = 6
    JOIN_EVENT_TEXT = 7
    LEAVE_EVENT_TEXT = 8
    SLASH_COMMAND_CHAT = 9
    CARTOGRAPHY_TEXT = 10
    KICK_COMMAND = 11
    TITLE_COMMAND = 12
    SUMMON_COMMAND = 13
    SERVER_FORM = 14
    DATA_DRIVEN_UI = 15


class ItemStackRequestData:
    client_request_id: ItemStackRequestId
    actions: list[ItemStackRequestAction]
    strings_to_filter: list[str]
    strings_to_filter_origin: TextProcessingEventOrigin = field(type=int32)
