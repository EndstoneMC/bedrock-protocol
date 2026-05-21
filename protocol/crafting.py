import uuid
from enum import IntEnum

from protocol import field, packet, type, uint8, uvarint32, value, varint32
from protocol.inventory import ItemDescriptorCount, NetworkItemInstanceDescriptor

package = "bedrock.protocol"


class CraftingDataEntryType(IntEnum):
    SHAPELESS_RECIPE = 0
    SHAPED_RECIPE = 1
    FURNACE_RECIPE = value(2, until=975)
    FURNACE_AUX_RECIPE = value(3, until=975)
    MULTI_RECIPE = 4
    USER_DATA_SHAPELESS_RECIPE = 5
    SHAPELESS_CHEMISTRY_RECIPE = 6
    SHAPED_CHEMISTRY_RECIPE = 7
    SMITHING_TRANSFORM_RECIPE = 8
    SMITHING_TRIM_RECIPE = 9
    COUNT = value(sentinel=True)


@type(since=685)
class RecipeUnlockingRequirement:
    class UnlockingContext(IntEnum):
        NONE = 0
        ALWAYS_UNLOCKED = 1
        PLAYER_IN_WATER = 2
        PLAYER_HAS_MANY_ITEMS = 3

    context: UnlockingContext = field(type=uint8)
    ingredients: list[ItemDescriptorCount] = field(
        when=lambda p: p.context == UnlockingContext.NONE
    )


class ShapelessRecipe:
    recipe_id: str
    ingredients: list[ItemDescriptorCount]
    results: list[NetworkItemInstanceDescriptor]
    uuid: uuid.UUID
    tag: str
    priority: varint32
    unlocking_requirement: RecipeUnlockingRequirement = field(since=685)
    net_id: uvarint32


class UserDataShapelessRecipe(ShapelessRecipe):
    pass


class ShapelessChemistryRecipe(ShapelessRecipe):
    pass


class MultiRecipe:
    uuid: uuid.UUID
    net_id: uvarint32


class SmithingTransformRecipe:
    recipe_id: str
    template_ingredient: ItemDescriptorCount = field(since=582)
    base_ingredient: ItemDescriptorCount
    addition_ingredient: ItemDescriptorCount
    result: NetworkItemInstanceDescriptor
    tag: str
    net_id: uvarint32


class SmithingTrimRecipe:
    recipe_id: str
    template_ingredient: ItemDescriptorCount
    base_ingredient: ItemDescriptorCount
    addition_ingredient: ItemDescriptorCount
    tag: str
    net_id: uvarint32


class ShapedRecipe:
    pass


class ShapedChemistryRecipe(ShapedRecipe):
    pass


@type(deprecated=975)
class FurnaceRecipe:
    item_data: varint32
    item_result: NetworkItemInstanceDescriptor
    tag: str = field(since=354)


@type(deprecated=975)
class FurnaceAuxRecipe:
    item_data: varint32
    item_aux: varint32
    item_result: NetworkItemInstanceDescriptor
    tag: str = field(since=354)


class CraftingDataEntry:
    body: (
        ShapelessRecipe
        | ShapedRecipe
        | FurnaceRecipe
        | FurnaceAuxRecipe
        | MultiRecipe
        | UserDataShapelessRecipe
        | ShapelessChemistryRecipe
        | ShapedChemistryRecipe
        | SmithingTransformRecipe
        | SmithingTrimRecipe
    ) = field(tag=CraftingDataEntryType)


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


@packet(id=52)
class CraftingDataPacket:
    crafting_entries: list[CraftingDataEntry]
    potion_mixes: list[PotionMixDataEntry]
    container_mixes: list[ContainerMixDataEntry]
    material_reducers: list[MaterialReducerDataEntry]
    clear_recipes: bool
