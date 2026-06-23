from enum import IntEnum

from protocol import (
    field,
    int8,
    int16,
    int32,
    packet,
    uint8,
    uint16,
    uint32,
    uvarint32,
    varint32,
)
from protocol.actor import ActorRuntimeID, ActorUniqueID
from protocol.common import BlockPos, NetworkBlockPos, Vec3
from protocol.molang import MolangVersion

package = "bedrock.protocol"

# ContainerID is signed-char in BDS (SharedTypes::Legacy::ContainerID).
type ContainerID = int8


class ContainerType(IntEnum):
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


type ItemStackNetIdVariant = ItemStackNetId | ItemStackRequestId | ItemStackLegacyRequestId


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
    descriptor: ItemDescriptor
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


@packet(id=46)
class ContainerOpenPacket:
    """Sent from the server so that the client knows to open the container screen and do the chest opening animation."""

    container_id: ContainerID
    type: ContainerType = field(type=int8)
    pos: NetworkBlockPos = field(until=944)
    pos: BlockPos = field(since=944)
    entity_unique_id: ActorUniqueID


@packet(id=47)
class ContainerClosePacket:
    """After the game deletes the container manager on the client, the client sends this packet. Then the
    server deletes its container manager, and sends a packet back to the client that closes the container
    screen."""

    container_id: ContainerID
    container_type: ContainerType = field(type=int8, since=685)
    server_initiated_close: bool = field(since=419)


@packet(id=48)
class PlayerHotbarPacket:
    """Sent from the server when the player uses pick block on actors or blocks, in addition to the player
    uses the clear, give, or replace item command or if the serverplayer uses _sendAdditionalLevelData()."""

    selected_slot: uvarint32
    container_id: ContainerID
    should_select_slot: bool


@packet(id=49)
class InventoryContentPacket:
    """This is used for updating an entire container. Example uses include: player respawned, replace items
    command, 3rd party content calls sendInventory(), block picking."""

    inventory_id: uvarint32  # BDS mInventoryId (ContainerID)
    # v291..v407 wrote items as the legacy NetworkItemInstanceDescriptor; from v407
    # the wire encoding switched to NetworkItemStackDescriptor (the "net item" form).
    slots: list[NetworkItemInstanceDescriptor] = field(until=407)
    slots: list[NetworkItemStackDescriptor] = field(since=407)
    # v712 wrote a bare uvarint32 dynamic_id where BDS keeps the full FullContainerName;
    # v729 elevated it to the structured (container_slot + optional uint32) form;
    # v748 dropped the trailing dynamic_container_size and appended a storage item.
    dynamic_id_v712: uvarint32 = field(since=712, until=729)
    full_container_name: FullContainerName = field(since=729)
    dynamic_container_size: uvarint32 = field(since=729, until=748)
    storage_item: NetworkItemStackDescriptor = field(since=748)


@packet(id=50)
class InventorySlotPacket:
    """Updates one slot in an inventory rather than the whole thing. So like animal inventory (horses,
    donkeys, etc) and chests. Hotbar, offhand, and some player inventory changes."""

    inventory_id: uvarint32  # BDS mInventoryId (ContainerID)
    slot: uvarint32
    # v975 wrapped the optional cousins (full container name + storage item) ahead
    # of the slot item; earlier versions wrote them inline (or not at all).
    full_container_name: FullContainerName | None = field(since=975)
    storage_item: SerializedNetworkItemStackDescriptor | None = field(since=975)
    # v712 wrote only a bare uvarint32 dynamic_id where v729+ writes the structured
    # FullContainerName; v729 added a trailing dynamic_container_size that v748
    # replaced with a storage item.
    dynamic_id_v712: uvarint32 = field(since=712, until=729)
    full_container_name_v729: FullContainerName = field(since=729, until=975)
    dynamic_container_size: uvarint32 = field(since=729, until=748)
    storage_item_v748: NetworkItemStackDescriptor = field(since=748, until=975)
    # v291..v407 wrote items as the legacy NetworkItemInstanceDescriptor; from v407
    # the wire encoding switched to NetworkItemStackDescriptor.
    item: NetworkItemInstanceDescriptor = field(until=407)
    item: NetworkItemStackDescriptor = field(since=407, until=975)
    item: SerializedNetworkItemStackDescriptor = field(since=975)


@packet(id=51)
class ContainerSetDataPacket:
    """This is sent from the server basically any time that the "cooking" state of the brewing stand or the
    furnace changes (i.e. the loading bar)."""

    container_id: ContainerID
    id: varint32
    value: varint32


class CreativeItemNetId:
    raw_id: uvarint32


class CreativeItemCategory(IntEnum):
    ALL = 0
    CONSTRUCTION = 1
    NATURE = 2
    EQUIPMENT = 3
    ITEMS = 4
    ITEM_COMMAND_ONLY = 5
    UNDEFINED = 6


class CreativeGroupInfoDescription:
    creative_item_category: CreativeItemCategory = field(type=int32)
    name: str
    icon: NetworkItemInstanceDescriptor


class CreativeItemEntryDescription:
    creative_item_net_id: CreativeItemNetId
    item_descriptor: NetworkItemInstanceDescriptor
    group_index: uvarint32 = field(since=776)


@packet(id=145, since=407)
class CreativeContentPacket:
    groups: list[CreativeGroupInfoDescription] = field(since=776)
    contents: list[CreativeItemEntryDescription]


class ItemStackNetResult(IntEnum):
    SUCCESS = 0
    ERROR = 1
    INVALID_REQUEST_ACTION_TYPE = 2
    ACTION_REQUEST_NOT_ALLOWED = 3
    SCREEN_HANDLER_END_REQUEST_FAILED = 4
    ITEM_REQUEST_ACTION_HANDLER_COMMIT_FAILED = 5
    INVALID_REQUEST_CRAFT_ACTION_TYPE = 6
    INVALID_CRAFT_REQUEST = 7
    INVALID_CRAFT_REQUEST_SCREEN = 8
    INVALID_CRAFT_RESULT = 9
    INVALID_CRAFT_RESULT_INDEX = 10
    INVALID_CRAFT_RESULT_ITEM = 11
    INVALID_ITEM_NET_ID = 12
    MISSING_CREATED_OUTPUT_CONTAINER = 13
    FAILED_TO_SET_CREATED_ITEM_OUTPUT_SLOT = 14
    REQUEST_ALREADY_IN_PROGRESS = 15
    FAILED_TO_INIT_SPARSE_CONTAINER = 16
    RESULT_TRANSFER_FAILED = 17
    EXPECTED_ITEM_SLOT_NOT_FULLY_CONSUMED = 18
    EXPECTED_ANYWHERE_ITEM_NOT_FULLY_CONSUMED = 19
    ITEM_ALREADY_CONSUMED_FROM_SLOT = 20
    CONSUMED_TOO_MUCH_FROM_SLOT = 21
    MISMATCH_SLOT_EXPECTED_CONSUMED_ITEM = 22
    MISMATCH_SLOT_EXPECTED_CONSUMED_ITEM_NET_ID_VARIANT = 23
    FAILED_TO_MATCH_EXPECTED_SLOT_CONSUMED_ITEM = 24
    FAILED_TO_MATCH_EXPECTED_ALLOWED_ANYWHERE_CONSUMED_ITEM = 25
    CONSUMED_ITEM_OUT_OF_ALLOWED_SLOT_RANGE = 26
    CONSUMED_ITEM_NOT_ALLOWED = 27
    PLAYER_NOT_IN_CREATIVE_MODE = 28
    INVALID_EXPERIMENTAL_RECIPE_REQUEST = 29
    FAILED_TO_CRAFT_CREATIVE = 30
    FAILED_TO_GET_LEVEL_RECIPE = 31
    FAILED_TO_FIND_RECIPE_BY_NET_ID = 32
    MISMATCHED_CRAFTING_SIZE = 33
    MISSING_INPUT_SPARSE_CONTAINER = 34
    MISMATCHED_RECIPE_FOR_INPUT_GRID_ITEMS = 35
    EMPTY_CRAFT_RESULTS = 36
    FAILED_TO_ENCHANT = 37
    MISSING_INPUT_ITEM = 38
    INSUFFICIENT_PLAYER_LEVEL_TO_ENCHANT = 39
    MISSING_MATERIAL_ITEM = 40
    MISSING_ACTOR = 41
    UNKNOWN_PRIMARY_EFFECT = 42
    PRIMARY_EFFECT_OUT_OF_RANGE = 43
    PRIMARY_EFFECT_UNAVAILABLE = 44
    SECONDARY_EFFECT_OUT_OF_RANGE = 45
    SECONDARY_EFFECT_UNAVAILABLE = 46
    DST_CONTAINER_EQUAL_TO_CREATED_OUTPUT_CONTAINER = 47
    DST_CONTAINER_AND_SLOT_EQUAL_TO_SRC_CONTAINER_AND_SLOT = 48
    FAILED_TO_VALIDATE_SRC_SLOT = 49
    FAILED_TO_VALIDATE_DST_SLOT = 50
    INVALID_ADJUSTED_AMOUNT = 51
    INVALID_ITEM_SET_TYPE = 52
    INVALID_TRANSFER_AMOUNT = 53
    CANNOT_SWAP_ITEM = 54
    CANNOT_PLACE_ITEM = 55
    UNHANDLED_ITEM_SET_TYPE = 56
    INVALID_REMOVED_AMOUNT = 57
    INVALID_REGION = 58
    CANNOT_DROP_ITEM = 59
    CANNOT_DESTROY_ITEM = 60
    INVALID_SOURCE_CONTAINER = 61
    ITEM_NOT_CONSUMED = 62
    INVALID_NUM_CRAFTS = 63
    INVALID_CRAFT_RESULT_STACK_SIZE = 64
    CANNOT_REMOVE_ITEM = 65
    CANNOT_CONSUME_ITEM = 66
    SCREEN_STACK_ERROR = 67


class ItemStackResponseSlotInfo:
    requested_slot: uint8
    slot: uint8
    amount: uint8
    item_stack_net_id: ItemStackNetId
    custom_name: str = field(since=422)
    durability_correction: varint32 = field(since=428, until=766)
    filtered_custom_name: str = field(since=766)
    durability_correction: varint32 = field(since=766)


class ItemStackResponseContainerInfo:
    container_slot_type: uint8 = field(until=712)  # pre-v776, BDS-invisible; trust CloudburstMC
    full_container_name: FullContainerName = field(since=712)
    slots: list[ItemStackResponseSlotInfo]


class ItemStackResponseInfo:
    success: bool = field(until=419)
    result: ItemStackNetResult = field(type=uint8, since=419)
    client_request_id: int32 = field(type=varint32)
    containers: list[ItemStackResponseContainerInfo] = field(when=lambda p: p.success, until=419)
    containers: list[ItemStackResponseContainerInfo] = field(
        when=lambda p: p.result == ItemStackNetResult.SUCCESS, since=419
    )


@packet(id=148, since=407)
class ItemStackResponsePacket:
    responses: list[ItemStackResponseInfo]


@packet(id=31)
class MobEquipmentPacket:
    runtime_id: ActorRuntimeID
    item: NetworkItemStackDescriptor = field(until=975)
    item: SerializedNetworkItemStackDescriptor = field(since=975)
    slot: uint8
    selected_slot: uint8
    container_id: ContainerID


class ArmorSlot(IntEnum):
    HEAD = 0
    TORSO = 1
    LEGS = 2
    FEET = 3
    BODY = 4


class ArmorSlotAndDamagePair:
    armor_slot: ArmorSlot = field(type=varint32)
    damage: int16


@packet(id=149, since=407)
class PlayerArmorDamagePacket:
    """Sent from server whenever the player's armor takes damage."""

    # COMPILER_EXTENSION_NEEDED: until=844 the wire is a uint8 bitfield over ArmorSlot
    # followed by N varint32 damages where N = popcount(bitfield) and the i-th damage
    # corresponds to the i-th set bit. The max bit index is 3 in v407..v712 (HEAD..FEET)
    # and 4 in v712..v844 (adds BODY). Cannot be expressed with field(when=) per-slot
    # because the DSL has no popcount nor "the bit at index i is set" predicate over an
    # integer-valued bitfield. (At v844 the wire became a regular uvarint32-prefixed
    # list[ArmorSlotAndDamagePair], which we could model directly if v844+ were the
    # only era to support.)
    pairs: list[ArmorSlotAndDamagePair] = field(since=844)


@packet(id=317, since=729)
class ContainerRegistryCleanupPacket:
    """This is used to trigger a clientside cleanup of the dynamic container registry."""

    removed_containers: list[FullContainerName]


# TODO: at v975 CloudburstMC switched EnchantData.Type from uint8 to uvarint32,
# but gophertunnel still marshals EnchantmentInstance.Type as a plain uint8 on
# master. Modelled per CloudburstMC; revisit if gophertunnel catches up the
# other way.
class EnchantmentInstance:
    enchant_type: int32 = field(type=uint8, until=975)
    enchant_type: int32 = field(type=uvarint32, since=975)
    level: int32 = field(type=uint8)


class ItemEnchants:
    slot: int32 = field(endian="little")
    enchants_0: list[EnchantmentInstance]
    enchants_1: list[EnchantmentInstance]
    enchants_2: list[EnchantmentInstance]


class ItemEnchantOption:
    cost: int32 = field(type=uvarint32, until=975)
    cost: int32 = field(type=uint8, since=975)
    enchants: ItemEnchants
    enchant_name: str
    enchant_net_id: uvarint32


@packet(id=146, since=407)
class PlayerEnchantOptionsPacket:
    """Sent by the server to update the enchantment options displayed when the user opens the enchantment
    table and puts an item in."""

    options: list[ItemEnchantOption]
