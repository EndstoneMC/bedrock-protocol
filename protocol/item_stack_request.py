from enum import IntEnum

from protocol import field, int16, int32, uint8, uint32, uvarint32, varint32
from protocol.inventory import (
    ContainerEnumName,
    ItemStackRequestId,
    NetworkItemInstanceDescriptor,
)

package = "bedrock.protocol"


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
    number_of_crafts: uint8


class CraftRecipeAutoStackRequestAction:
    # BDS' header shows `mIngredients, mNumIngredients (u8)` but gophertunnel
    # writes the second u8 between number_of_crafts and the ingredients list
    # (and calls it TimesCrafted). The golden bytes match the gophertunnel
    # order, so until a BDS .cpp / IDA trace says otherwise we follow that.
    recipe_network_id: uvarint32
    number_of_crafts: uint8
    times_crafted: uint8
    ingredients: list[ItemDescriptorCount]


class CraftCreativeStackRequestAction:
    creative_item_network_id: uvarint32
    number_of_crafts: uint8


class CraftRecipeOptionalStackRequestAction:
    recipe_network_id: uvarint32
    filter_string_index: int32


class CraftRepairAndDisenchantStackRequestAction:
    recipe_network_id: uvarint32
    number_of_crafts: uint8
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
