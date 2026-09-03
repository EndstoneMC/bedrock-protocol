"""The item-stack request/response protocol: world/inventory/network/ --
request actions, responses, and the cereal namespace carrier."""

from enum import IntEnum, auto
from typing import Literal

from protocol import field, int16, int32, packet, type, uint8, uint16, uvarint32, varint32
from protocol.crafting import (
    CreativeItemNetId,
    RecipeNetId,
    SerializedNetworkItemInstanceDescriptor,
    SerializedRecipeIngredient,
)
from protocol.inventory import FullContainerName
from protocol.item import ItemStackNetId, ItemStackRequestId
from protocol.molang import MolangVersion

package = "bedrock.protocol"


class ItemStackRequestActionType(IntEnum, uint8):
    TAKE = 0
    PLACE = 1
    SWAP = 2
    DROP = 3
    DESTROY = 4
    CONSUME = 5
    CREATE = 6
    PLACE_IN_ITEM_CONTAINER_DEPRECATED = 7
    TAKE_FROM_ITEM_CONTAINER_DEPRECATED = 8
    SCREEN_LAB_TABLE_COMBINE = 9
    SCREEN_BEACON_PAYMENT = 10
    SCREEN_HUD_MINE_BLOCK = 11
    CRAFT_RECIPE = 12
    CRAFT_RECIPE_AUTO = 13
    CRAFT_CREATIVE = 14
    CRAFT_RECIPE_OPTIONAL = 15
    CRAFT_REPAIR_AND_DISENCHANT = 16
    CRAFT_LOOM = 17
    CRAFT_NON_IMPLEMENTED_DEPRECATEDASKTYLAING = 18
    CRAFT_RESULTS_DEPRECATEDASKTYLAING = 19


class ItemStackNetResult(IntEnum, uint8):
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


class TextProcessingEventOrigin(IntEnum):
    UNKNOWN = -1
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
    COUNT = auto()


@type(until=2168)
class RedactableString:
    unredacted_string: str
    redacted_string: str


@type(since=2168)
class RedactableString:
    unredacted_string: str
    redacted_string: str | None


@type(until=2168)
class ItemStackResponseSlotInfo:
    requested_slot: uint8
    slot: uint8
    amount: uint8
    item_stack_net_id: ItemStackNetId
    custom_name: RedactableString
    durability_correction: int16 = field(type=varint32)


@type(since=2168)
class ItemStackResponseSlotInfo:
    requested_slot: uint8
    slot: uint8
    amount: uint8
    _true: Literal[True] = field(until=2192)
    item_stack_net_id: ItemStackNetId | None
    custom_name: RedactableString
    durability_correction: int16 = field(type=varint32)


class ItemStackResponseContainerInfo:
    full_container_name: FullContainerName
    slots: list[ItemStackResponseSlotInfo]


@type(until=2168)
class ItemStackResponseInfo:
    result: ItemStackNetResult
    client_request_id: ItemStackRequestId
    containers: list[ItemStackResponseContainerInfo] = field(when=lambda r: r.result == ItemStackNetResult.SUCCESS)


@type(since=2168)
class ItemStackResponseInfo:
    result: ItemStackNetResult
    client_request_id: ItemStackRequestId
    _true: Literal[True] = field(until=2192)
    containers: list[ItemStackResponseContainerInfo] | None


@packet(id=148)
class ItemStackResponsePacket:
    responses: list[ItemStackResponseInfo]


@type(until=2168)
class ItemStackRequestSlotInfo:
    full_container_name: FullContainerName
    slot: uint8
    net_id_variant: varint32


@type(until=2168)
class ItemStackRequestActionTake:
    amount: uint8
    src: ItemStackRequestSlotInfo
    dst: ItemStackRequestSlotInfo


@type(until=2168)
class ItemStackRequestActionPlace:
    amount: uint8
    src: ItemStackRequestSlotInfo
    dst: ItemStackRequestSlotInfo


@type(until=2168)
class ItemStackRequestActionSwap:
    src: ItemStackRequestSlotInfo
    dst: ItemStackRequestSlotInfo


@type(until=2168)
class ItemStackRequestActionDrop:
    amount: uint8
    src: ItemStackRequestSlotInfo
    randomly: bool


@type(until=2168)
class ItemStackRequestActionDestroy:
    amount: uint8
    src: ItemStackRequestSlotInfo


@type(until=2168)
class ItemStackRequestActionConsume:
    amount: uint8
    src: ItemStackRequestSlotInfo


@type(until=2168)
class ItemStackRequestActionCreate:
    results_index: uint8


@type(until=2168)
class ItemStackRequestActionLabTableCombine:
    pass


@type(until=2168)
class ItemStackRequestActionBeaconPayment:
    primary_effect_id: varint32
    secondary_effect_id: varint32


@type(until=2168)
class ItemStackRequestActionMineBlock:
    slot: varint32
    predicted_durability: varint32
    net_id_variant: varint32


@type(until=2168)
class ItemStackRequestActionCraftRecipe:
    recipe_net_id: RecipeNetId
    num_crafts: uint8


@type(until=2168)
class ItemStackRequestActionCraftRecipeAuto:
    recipe_net_id: RecipeNetId
    num_crafts: uint8
    num_ingredients: uint8
    ingredients: list[SerializedRecipeIngredient]


@type(until=2168)
class ItemStackRequestActionCraftCreative:
    creative_item_net_id: CreativeItemNetId
    num_crafts: uint8


@type(until=2168)
class ItemStackRequestActionCraftRecipeOptional:
    recipe_net_id: RecipeNetId
    filtered_string_index: int32


@type(until=2168)
class ItemStackRequestActionCraftGrindstone:
    recipe_net_id: uvarint32
    num_crafts: uint8
    repair_cost: varint32


@type(until=2168)
class ItemStackRequestActionCraftLoom:
    pattern_name_id: str
    num_crafts: uint8


@type(until=2168)
class ItemStackRequestActionCraftNonImplemented_DEPRECATEDASKTYLAING:
    pass


@type(until=2168)
class ItemStackRequestActionCraftResults_DEPRECATEDASKTYLAING:
    craft_results: list[SerializedNetworkItemInstanceDescriptor]
    num_crafts: uint8


@type(until=2168)
class ItemStackRequestData:
    client_request_id: ItemStackRequestId
    actions: list[
        ItemStackRequestActionTake
        | ItemStackRequestActionPlace
        | ItemStackRequestActionSwap
        | ItemStackRequestActionDrop
        | ItemStackRequestActionDestroy
        | ItemStackRequestActionConsume
        | ItemStackRequestActionCreate
        | None
        | None
        | ItemStackRequestActionLabTableCombine
        | ItemStackRequestActionBeaconPayment
        | ItemStackRequestActionMineBlock
        | ItemStackRequestActionCraftRecipe
        | ItemStackRequestActionCraftRecipeAuto
        | ItemStackRequestActionCraftCreative
        | ItemStackRequestActionCraftRecipeOptional
        | ItemStackRequestActionCraftGrindstone
        | ItemStackRequestActionCraftLoom
        | ItemStackRequestActionCraftNonImplemented_DEPRECATEDASKTYLAING
        | ItemStackRequestActionCraftResults_DEPRECATEDASKTYLAING
    ]
    strings_to_filter: list[str]
    strings_to_filter_origin: TextProcessingEventOrigin = field(type=int32)


# TODO: ItemStackRequestCereal is a BDS namespace, and the packet's element type is
# ItemStackRequestPacketData::RequestData, an identically-bodied struct in a second
# namespace. The DSL has no namespace, so both collapse onto this one scoping class.
@type(since=2168)
class ItemStackRequestCereal:
    class ItemDescriptorType(IntEnum, uint8):
        EMPTY = 0
        ITEM_NAME = 1
        MOLANG = 2
        ITEM_TAG = 3

    class EmptyItemDescriptorData:
        descriptor_type: ItemDescriptorType

    class ItemNameDescriptorData:
        descriptor_type: ItemDescriptorType
        full_name: str
        aux_value: varint32

    class MolangItemDescriptorData:
        descriptor_type: ItemDescriptorType
        tag_expression: str
        molang_version: MolangVersion = field(type=int16)

    class ItemTagDescriptorData:
        descriptor_type: ItemDescriptorType
        item_tag: str

    class NetworkItemInstanceDescriptorData:
        item_descriptor: (
            EmptyItemDescriptorData | ItemNameDescriptorData | MolangItemDescriptorData | ItemTagDescriptorData
        )
        stack_size: uint16
        block_runtime_id: uvarint32
        user_data_buffer: bytes

    class RecipeIngredientData:
        item_descriptor: (
            EmptyItemDescriptorData | ItemNameDescriptorData | MolangItemDescriptorData | ItemTagDescriptorData
        )
        stack_size: uint16

    class SlotInfoData:
        full_container_name: FullContainerName
        slot: uint8
        net_id_variant: int32

    class TakeActionData:
        action_type: ItemStackRequestActionType
        amount: uint8
        source: SlotInfoData
        destination: SlotInfoData

    class PlaceActionData:
        action_type: ItemStackRequestActionType
        amount: uint8
        source: SlotInfoData
        destination: SlotInfoData

    class SwapActionData:
        action_type: ItemStackRequestActionType
        source: SlotInfoData
        destination: SlotInfoData

    class DropActionData:
        action_type: ItemStackRequestActionType
        amount: uint8
        source: SlotInfoData
        randomly: bool

    class DestroyActionData:
        action_type: ItemStackRequestActionType
        amount: uint8
        source: SlotInfoData

    class ConsumeActionData:
        action_type: ItemStackRequestActionType
        amount: uint8
        source: SlotInfoData

    class CreateActionData:
        action_type: ItemStackRequestActionType
        results_index: uint8

    class LabTableCombineActionData:
        action_type: ItemStackRequestActionType

    class BeaconPaymentActionData:
        action_type: ItemStackRequestActionType
        primary_effect_id: varint32
        secondary_effect_id: varint32

    class MineBlockActionData:
        action_type: ItemStackRequestActionType
        slot: varint32
        predicted_durability: varint32
        net_id_variant: int32

    class CraftRecipeActionData:
        action_type: ItemStackRequestActionType
        recipe_net_id: RecipeNetId
        num_crafts: uint8

    class CraftRecipeAutoActionData:
        action_type: ItemStackRequestActionType
        recipe_net_id: RecipeNetId
        num_crafts: uint8
        ingredients: list[RecipeIngredientData]

    class CraftCreativeActionData:
        action_type: ItemStackRequestActionType
        creative_item_net_id: uvarint32
        num_crafts: uint8

    class CraftRecipeOptionalActionData:
        action_type: ItemStackRequestActionType
        recipe_net_id: RecipeNetId
        filtered_string_index: int32

    class CraftRepairAndDisenchantActionData:
        action_type: ItemStackRequestActionType
        recipe_net_id: int32
        num_crafts: uint8
        repair_cost: varint32

    class CraftLoomActionData:
        action_type: ItemStackRequestActionType
        pattern_name_id: str
        num_crafts: uint8

    class CraftNonImplementedActionData:
        action_type: ItemStackRequestActionType

    class CraftResultsActionData:
        action_type: ItemStackRequestActionType
        craft_results: list[NetworkItemInstanceDescriptorData]
        num_crafts: uint8

    class RequestData:
        client_request_id: ItemStackRequestId
        actions: list[
            TakeActionData
            | PlaceActionData
            | SwapActionData
            | DropActionData
            | DestroyActionData
            | ConsumeActionData
            | CreateActionData
            | LabTableCombineActionData
            | BeaconPaymentActionData
            | MineBlockActionData
            | CraftRecipeActionData
            | CraftRecipeAutoActionData
            | CraftCreativeActionData
            | CraftRecipeOptionalActionData
            | CraftRepairAndDisenchantActionData
            | CraftLoomActionData
            | CraftNonImplementedActionData
            | CraftResultsActionData
        ]
        strings_to_filter: list[str]
        strings_to_filter_origin: TextProcessingEventOrigin = field(type=int32)


@packet(id=147, until=2168)
class ItemStackRequestPacket:
    requests: list[ItemStackRequestData]


@packet(id=147, since=2168)
class ItemStackRequestPacket:
    requests: list[ItemStackRequestCereal.RequestData]
