from enum import IntEnum

from protocol import field, int16, int32, uint8, uint16, uint32, uvarint32, varint32
from protocol.common import BlockPos, Vec3
from protocol.molang import MolangVersion

package = "bedrock.protocol"


class NetworkItemStackDescriptor:
    id: varint32
    with field(when=lambda p: p.id != 0):
        stack_size: uint16
        aux_value: uvarint32
        net_id_variant: varint32 | None
        block_runtime_id: varint32
        user_data_buffer: bytes


class NetworkItemInstanceDescriptor:
    id: varint32
    with field(when=lambda p: p.id != 0):
        stack_size: uint16
        aux_value: uvarint32
        block_runtime_id: varint32
        user_data_buffer: bytes


class ItemStackNetId:
    id: varint32


class ItemStackRequestId:
    id: varint32


class ItemStackLegacyRequestId:
    id: varint32


type ItemStackNetIdVariant = (
    ItemStackNetId | ItemStackRequestId | ItemStackLegacyRequestId
)


class SerializedNetworkItemStackDescriptor:
    """Mirror of the BDS type cerealizer<NetworkItemStackDescriptor>::SerializedData."""

    id: int16
    stack_size: uint16
    aux_value: uvarint32
    net_id_variant: ItemStackNetIdVariant | None
    block_runtime_id: uvarint32
    user_data_buffer: bytes


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
    from_item_descriptor: NetworkItemStackDescriptor
    to_item_descriptor: NetworkItemStackDescriptor


class InventoryTransaction:
    actions: list[InventoryAction]


class LegacySetSlot:
    container_enum: ContainerEnumName = field(type=uint8)
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
    pos: BlockPos
    face: varint32
    slot: varint32
    item: NetworkItemStackDescriptor
    from_pos: Vec3
    click_pos: Vec3
    target_block_id: uvarint32
    client_predicted_result: PredictedResult = field(type=uint8, since=712)
    client_cooldown_state: ClientCooldownState = field(type=uint8, since=944)


class PackedItemUseLegacyInventoryTransaction:
    id: ItemStackLegacyRequestId
    slots: list[LegacySetSlot] = field(
        when=lambda p: p.id.id < -1 and (p.id.id & 1) == 0,
    )
    transaction: ItemUseInventoryTransaction


class FullContainerName:
    name: ContainerEnumName = field(type=uint8)
    dynamic_id: uint32 | None


class ItemStackRequestSlotInfo:
    full_container_name: FullContainerName
    slot: uint8
    net_id_variant: varint32


class InvalidItemDescriptor:
    pass


class InternalItemDescriptor:
    item_id: int16
    aux_value: int16 = field(when=lambda p: p.item_id != 0)


class MolangDescriptor:
    expression_tags: str
    version: MolangVersion = field(type=uint8)


class ItemTagDescriptor:
    item_tag: str


class DeferredDescriptor:
    full_name: str
    aux_value: int16


class ComplexAliasDescriptor:
    full_name: str


type ItemDescriptor = (
    InvalidItemDescriptor
    | InternalItemDescriptor
    | MolangDescriptor
    | ItemTagDescriptor
    | DeferredDescriptor
    | ComplexAliasDescriptor
)


class ItemDescriptorCount:
    descriptor: ItemDescriptor = field(tag=uint8)
    count: varint32


class ItemStackRequestActionType(IntEnum):
    TAKE = 0
    PLACE = 1
    SWAP = 2
    DROP = 3
    DESTROY = 4
    CONSUME = 5
    CREATE = 6
    PLACE_IN_ITEM_CONTAINER = 7
    TAKE_FROM_ITEM_CONTAINER = 8
    SCREEN_LAB_TABLE_COMBINE = 9
    SCREEN_BEACON_PAYMENT = 10
    SCREEN_HUD_MINE_BLOCK = 11
    CRAFT_RECIPE = 12
    CRAFT_RECIPE_AUTO = 13
    CRAFT_CREATIVE = 14
    CRAFT_RECIPE_OPTIONAL = 15
    CRAFT_REPAIR_AND_DISENCHANT = 16
    CRAFT_LOOM = 17
    CRAFT_NON_IMPLEMENTED = 18
    CRAFT_RESULTS = 19


class ItemStackRequestActionTake:
    amount: uint8
    src: ItemStackRequestSlotInfo
    dst: ItemStackRequestSlotInfo


class ItemStackRequestActionPlace:
    amount: uint8
    src: ItemStackRequestSlotInfo
    dst: ItemStackRequestSlotInfo


class ItemStackRequestActionSwap:
    src: ItemStackRequestSlotInfo
    dst: ItemStackRequestSlotInfo


class ItemStackRequestActionDrop:
    amount: uint8
    src: ItemStackRequestSlotInfo
    randomly: bool


class ItemStackRequestActionDestroy:
    amount: uint8
    src: ItemStackRequestSlotInfo


class ItemStackRequestActionConsume:
    amount: uint8
    src: ItemStackRequestSlotInfo


class ItemStackRequestActionCreate:
    results_index: uint8


class ItemStackRequestActionPlaceInItemContainer:
    amount: uint8
    src: ItemStackRequestSlotInfo
    dst: ItemStackRequestSlotInfo


class ItemStackRequestActionTakeFromItemContainer:
    amount: uint8
    src: ItemStackRequestSlotInfo
    dst: ItemStackRequestSlotInfo


class ItemStackRequestActionLabTableCombine:
    pass


class ItemStackRequestActionBeaconPayment:
    primary_effect_id: varint32
    secondary_effect_id: varint32


class ItemStackRequestActionMineBlock:
    slot: varint32
    predicted_durability: varint32
    net_id_variant: varint32


class ItemStackRequestActionCraftRecipe:
    recipe_net_id: uvarint32
    num_crafts: uint8


class ItemStackRequestActionCraftRecipeAuto:
    recipe_net_id: uvarint32
    num_requested_crafts: uint8  # always set to the same value as num_crafts
    num_crafts: uint8
    ingredients: list[ItemDescriptorCount]


class ItemStackRequestActionCraftCreative:
    recipe_net_id: uvarint32
    num_crafts: uint8


class ItemStackRequestActionCraftRecipeOptional:
    recipe_net_id: uvarint32
    filtered_string_index: int32


class ItemStackRequestActionCraftGrindstone:
    recipe_net_id: uvarint32
    num_crafts: uint8
    repair_cost: varint32


class ItemStackRequestActionCraftLoom:
    pattern_name_id: str
    num_crafts: uint8


class ItemStackRequestActionCraftNonImplemented:
    pass


class ItemStackRequestActionCraftResults:
    craft_results: list[NetworkItemInstanceDescriptor]
    num_crafts: uint8


type ItemStackRequestAction = (
    ItemStackRequestActionTake
    | ItemStackRequestActionPlace
    | ItemStackRequestActionSwap
    | ItemStackRequestActionDrop
    | ItemStackRequestActionDestroy
    | ItemStackRequestActionConsume
    | ItemStackRequestActionCreate
    | ItemStackRequestActionPlaceInItemContainer
    | ItemStackRequestActionTakeFromItemContainer
    | ItemStackRequestActionLabTableCombine
    | ItemStackRequestActionBeaconPayment
    | ItemStackRequestActionMineBlock
    | ItemStackRequestActionCraftRecipe
    | ItemStackRequestActionCraftRecipeAuto
    | ItemStackRequestActionCraftCreative
    | ItemStackRequestActionCraftRecipeOptional
    | ItemStackRequestActionCraftGrindstone
    | ItemStackRequestActionCraftLoom
    | ItemStackRequestActionCraftNonImplemented
    | ItemStackRequestActionCraftResults
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
