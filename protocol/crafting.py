"""Packets and types relating to recipes."""

import uuid
from enum import IntEnum, auto

from protocol import field, int32, packet, type, uint8, uint16, uint32, uvarint32, value, varint32
from protocol.item import ItemDescriptor, SerializedNetworkItemInstanceDescriptor

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"
go_package = "github.com/EndstoneMC/bedrock-protocol/go/protocol"


type RecipeNetId = uvarint32


@type(until=2168)
class SerializedRecipeIngredient:
    descriptor: ItemDescriptor
    stack_size: uint16 = field(type=varint32)


@type(since=2168)
class SerializedRecipeIngredient:
    descriptor: dict[str, str]
    aux_value: varint32
    stack_size: varint32


class RecipeUnlockingRequirement:
    class UnlockingContext(IntEnum, int32):
        NONE = 0
        ALWAYS_UNLOCKED = 1
        PLAYER_IN_WATER = 2
        PLAYER_HAS_MANY_ITEMS = 3


@type(until=2168)
class SerializedRecipeUnlockingRequirement:
    context: RecipeUnlockingRequirement.UnlockingContext = field(type=uint8)
    ingredients: list[SerializedRecipeIngredient] = field(
        when=lambda r: r.context == RecipeUnlockingRequirement.UnlockingContext.NONE
    )


@type(since=2168)
class SerializedRecipeUnlockingRequirement:
    context: RecipeUnlockingRequirement.UnlockingContext
    ingredients: list[SerializedRecipeIngredient] | None


@type(until=2168)
class ShapedRecipePayload:
    recipe_id: str
    width: varint32
    height: varint32
    ingredients: list[SerializedRecipeIngredient] = field(count=lambda r: r.width * r.height)
    results: list[SerializedNetworkItemInstanceDescriptor]
    uuid: uuid.UUID
    tag: str
    priority: varint32
    assume_symmetry: bool = field(since=671)
    unlocking_requirement: SerializedRecipeUnlockingRequirement = field(since=685)
    net_id: RecipeNetId


@type(since=2168)
class ShapedRecipePayload:
    recipe_id: str
    width: varint32
    height: varint32
    ingredients: list[SerializedRecipeIngredient]
    results: list[SerializedNetworkItemInstanceDescriptor]
    uuid: uuid.UUID
    tag: str
    priority: varint32
    assume_symmetry: bool
    unlocking_requirement: SerializedRecipeUnlockingRequirement | None
    net_id: RecipeNetId


@type(until=2168)
class ShapelessRecipePayload:
    recipe_id: str
    ingredients: list[SerializedRecipeIngredient]
    results: list[SerializedNetworkItemInstanceDescriptor]
    uuid: uuid.UUID
    tag: str
    priority: varint32
    unlocking_requirement: SerializedRecipeUnlockingRequirement = field(since=685)
    net_id: RecipeNetId


@type(since=2168)
class ShapelessRecipePayload:
    recipe_id: str
    ingredients: list[SerializedRecipeIngredient]
    results: list[SerializedNetworkItemInstanceDescriptor]
    uuid: uuid.UUID
    tag: str
    priority: varint32
    unlocking_requirement: SerializedRecipeUnlockingRequirement | None
    net_id: RecipeNetId


class MultiRecipePayload:
    uuid: uuid.UUID
    net_id: RecipeNetId


class SmithingTransformRecipePayload:
    recipe_id: str
    template_ingredient: SerializedRecipeIngredient
    base_ingredient: SerializedRecipeIngredient
    addition_ingredient: SerializedRecipeIngredient
    result: SerializedNetworkItemInstanceDescriptor
    tag: str
    net_id: RecipeNetId


class SmithingTrimRecipePayload:
    recipe_id: str
    template_ingredient: SerializedRecipeIngredient
    base_ingredient: SerializedRecipeIngredient
    addition_ingredient: SerializedRecipeIngredient
    tag: str
    net_id: RecipeNetId


class PotionMixDataEntry:
    from_item_id: varint32
    from_item_aux: varint32
    reagent_item_id: varint32
    reagent_item_aux: varint32
    to_item_id: varint32
    to_item_aux: varint32


class ContainerMixDataEntry:
    from_item_id: varint32
    reagent_item_id: varint32
    to_item_id: varint32


class MaterialReducerEntryOutput:
    item_id: varint32
    item_count: varint32


class MaterialReducerDataEntry:
    from_item_key: varint32
    to_item_ids_and_counts: list[MaterialReducerEntryOutput]


@packet(id=52, until=2168)
class CraftingDataPacket:
    crafting_entries: list[CraftingDataEntry]
    potion_mix_entries: list[PotionMixDataEntry]
    container_mix_entries: list[ContainerMixDataEntry]
    material_reducer_entries: list[MaterialReducerDataEntry]
    clear_recipes: bool


@packet(id=52, since=2168)
class CraftingDataPacket:
    shaped_recipes: list[ShapedRecipePayload]
    shapeless_recipes: list[ShapelessRecipePayload]
    multi_recipes: list[MultiRecipePayload]
    user_data_shapeless_recipes: list[ShapelessRecipePayload]
    shapeless_chemistry_recipes: list[ShapelessRecipePayload]
    shaped_chemistry_recipes: list[ShapedRecipePayload]
    smithing_transform_recipes: list[SmithingTransformRecipePayload]
    smithing_trim_recipes: list[SmithingTrimRecipePayload]
    potion_mix_entries: list[PotionMixDataEntry]
    container_mix_entries: list[ContainerMixDataEntry]
    material_reducer_entries: list[MaterialReducerDataEntry]
    clear_recipes: bool


@packet(id=199)
class UnlockedRecipesPacket:
    class PacketType(IntEnum, uint32):
        EMPTY = 0
        INITIALLY_UNLOCKED_RECIPES = 1
        NEWLY_UNLOCKED_RECIPES = 2
        REMOVE_UNLOCKED_RECIPES = 3
        REMOVE_ALL_UNLOCKED_RECIPES = 4

    packet_type: PacketType = field(type=uint32)
    unlocked_recipes: list[str]


@type(until=2168)
class ShapedChemistryRecipePayload:
    recipe_id: str
    width: varint32
    height: varint32
    ingredients: list[SerializedRecipeIngredient] = field(count=lambda r: r.width * r.height)
    results: list[SerializedNetworkItemInstanceDescriptor]
    uuid: uuid.UUID
    tag: str
    priority: varint32
    assume_symmetry: bool = field(since=671)
    net_id: RecipeNetId


@type(until=2168)
class ShapelessChemistryRecipePayload:
    recipe_id: str
    ingredients: list[SerializedRecipeIngredient]
    results: list[SerializedNetworkItemInstanceDescriptor]
    uuid: uuid.UUID
    tag: str
    priority: varint32
    net_id: RecipeNetId


@type(until=2168)
class CraftingDataEntryType(IntEnum, int32):
    SHAPELESS_RECIPE = 0
    SHAPED_RECIPE = 1
    with value(until=975):
        FURNACE_RECIPE = 2
        FURNACE_AUX_RECIPE = 3
    MULTI_RECIPE = 4
    USER_DATA_SHAPELESS_RECIPE = 5
    SHAPELESS_CHEMISTRY_RECIPE = 6
    SHAPED_CHEMISTRY_RECIPE = 7
    SMITHING_TRANSFORM_RECIPE = 8
    SMITHING_TRIM_RECIPE = 9
    COUNT = auto()


@type(until=748)
class CraftingDataEntry:
    entry_type: CraftingDataEntryType
    shapeless_recipe: ShapelessRecipePayload = field(
        when=lambda e: e.entry_type == CraftingDataEntryType.SHAPELESS_RECIPE
    )
    shapeless_chemistry_recipe: ShapelessChemistryRecipePayload = field(
        when=lambda e: (
            e.entry_type
            in {CraftingDataEntryType.SHAPELESS_CHEMISTRY_RECIPE, CraftingDataEntryType.USER_DATA_SHAPELESS_RECIPE}
        )
    )
    shaped_recipe: ShapedRecipePayload = field(when=lambda e: e.entry_type == CraftingDataEntryType.SHAPED_RECIPE)
    shaped_chemistry_recipe: ShapedChemistryRecipePayload = field(
        when=lambda e: e.entry_type == CraftingDataEntryType.SHAPED_CHEMISTRY_RECIPE
    )
    multi_recipe: MultiRecipePayload = field(when=lambda e: e.entry_type == CraftingDataEntryType.MULTI_RECIPE)
    smithing_transform_recipe: SmithingTransformRecipePayload = field(
        when=lambda e: e.entry_type == CraftingDataEntryType.SMITHING_TRANSFORM_RECIPE
    )
    smithing_trim_recipe: SmithingTrimRecipePayload = field(
        when=lambda e: e.entry_type == CraftingDataEntryType.SMITHING_TRIM_RECIPE
    )
    item_data: varint32 = field(
        when=lambda e: e.entry_type in {CraftingDataEntryType.FURNACE_RECIPE, CraftingDataEntryType.FURNACE_AUX_RECIPE}
    )
    item_aux: varint32 = field(when=lambda e: e.entry_type == CraftingDataEntryType.FURNACE_AUX_RECIPE)
    with field(
        when=lambda e: e.entry_type in {CraftingDataEntryType.FURNACE_RECIPE, CraftingDataEntryType.FURNACE_AUX_RECIPE}
    ):
        item_result: SerializedNetworkItemInstanceDescriptor
        tag: str


@type(since=748, until=2168)
class CraftingDataEntry:
    entry_type: CraftingDataEntryType
    shapeless_recipe: ShapelessRecipePayload = field(
        when=lambda e: (
            e.entry_type in {CraftingDataEntryType.SHAPELESS_RECIPE, CraftingDataEntryType.USER_DATA_SHAPELESS_RECIPE}
        )
    )
    shapeless_chemistry_recipe: ShapelessChemistryRecipePayload = field(
        when=lambda e: e.entry_type == CraftingDataEntryType.SHAPELESS_CHEMISTRY_RECIPE
    )
    shaped_recipe: ShapedRecipePayload = field(when=lambda e: e.entry_type == CraftingDataEntryType.SHAPED_RECIPE)
    shaped_chemistry_recipe: ShapedChemistryRecipePayload = field(
        when=lambda e: e.entry_type == CraftingDataEntryType.SHAPED_CHEMISTRY_RECIPE
    )
    multi_recipe: MultiRecipePayload = field(when=lambda e: e.entry_type == CraftingDataEntryType.MULTI_RECIPE)
    smithing_transform_recipe: SmithingTransformRecipePayload = field(
        when=lambda e: e.entry_type == CraftingDataEntryType.SMITHING_TRANSFORM_RECIPE
    )
    smithing_trim_recipe: SmithingTrimRecipePayload = field(
        when=lambda e: e.entry_type == CraftingDataEntryType.SMITHING_TRIM_RECIPE
    )
    with field(until=975):
        item_data: varint32 = field(
            when=lambda e: (
                e.entry_type in {CraftingDataEntryType.FURNACE_RECIPE, CraftingDataEntryType.FURNACE_AUX_RECIPE}
            )
        )
        item_aux: varint32 = field(when=lambda e: e.entry_type == CraftingDataEntryType.FURNACE_AUX_RECIPE)
        item_result: SerializedNetworkItemInstanceDescriptor = field(
            when=lambda e: (
                e.entry_type in {CraftingDataEntryType.FURNACE_RECIPE, CraftingDataEntryType.FURNACE_AUX_RECIPE}
            )
        )
        tag: str = field(
            when=lambda e: (
                e.entry_type in {CraftingDataEntryType.FURNACE_RECIPE, CraftingDataEntryType.FURNACE_AUX_RECIPE}
            )
        )
