import uuid
from enum import IntEnum, auto

from protocol import field, int32, packet, type, uint8, uint32, uvarint32, value, varint32
from protocol.common import BlockPos, NetworkBlockPos
from protocol.inventory import ItemDescriptorCount, NetworkItemInstanceDescriptor

package = "bedrock.protocol"


@packet(id=141, since=388)
class AnvilDamagePacket:
    """Requests an anvil to be damaged."""

    damage: int32 = field(type=uint8)
    position: NetworkBlockPos = field(until=944)
    position: BlockPos = field(since=944)


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
    COUNT = auto()


@type(since=685)
class RecipeUnlockingRequirement:
    class UnlockingContext(IntEnum):
        NONE = 0
        ALWAYS_UNLOCKED = 1
        PLAYER_IN_WATER = 2
        PLAYER_HAS_MANY_ITEMS = 3

    context: UnlockingContext = field(type=uint8)
    ingredients: list[ItemDescriptorCount] = field(when=lambda p: p.context == UnlockingContext.NONE)


class ShapelessRecipe:
    recipe_id: str
    ingredients: list[ItemDescriptorCount]
    results: list[NetworkItemInstanceDescriptor]
    uuid: uuid.UUID
    tag: str
    priority: varint32
    unlocking_requirement: RecipeUnlockingRequirement = field(since=685)
    net_id: uvarint32


# BDS: UserDataShapelessRecipe (alias of ShapelessRecipe wire form).
class UserDataShapelessRecipe(ShapelessRecipe):
    pass


# BDS: ShapelessChemistryRecipe (alias of ShapelessRecipe wire form).
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


# BDS: ShapedRecipe. Ingredients are an inline width*height array with no
# length prefix -- the count comes from sibling fields.
class ShapedRecipe:
    recipe_id: str
    width: varint32
    height: varint32
    ingredients: list[ItemDescriptorCount] = field(count=lambda p: p.width * p.height)
    results: list[NetworkItemInstanceDescriptor]
    uuid: uuid.UUID
    tag: str
    priority: varint32
    assume_symmetry: bool = field(since=671)
    unlocking_requirement: RecipeUnlockingRequirement = field(since=685)
    net_id: uvarint32


# BDS: ShapedChemistryRecipe (alias of ShapedRecipe wire form).
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


# BDS: CraftingDataEntry. Polymorphic recipe record tagged by CraftingDataEntryType.
class CraftingDataEntry:
    recipe: (
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
    potion_mix_entries: list[PotionMixDataEntry] = field(since=388)
    container_mix_entries: list[ContainerMixDataEntry] = field(since=388)
    material_reducer_entries: list[MaterialReducerDataEntry] = field(since=465)
    clear_recipes: bool


class CraftingType(IntEnum):
    INVENTORY = 0
    CRAFTING = 1


@packet(id=53)
class CraftingEventPacket:
    container_id: uint8
    type: CraftingType = field(type=varint32)
    uuid: uuid.UUID
    inputs: list[NetworkItemInstanceDescriptor]
    outputs: list[NetworkItemInstanceDescriptor]


class LabTablePacketType(IntEnum):
    START_COMBINE = 0
    START_REACTION = 1
    RESET = 2


class LabTableReactionType(IntEnum):
    NONE = 0
    ICE_BOMB = 1
    BLEACH = 2
    ELEPHANT_TOOTHPASTE = 3
    FERTILIZER = 4
    HEAT_BLOCK = 5
    MAGNESIUM_SALTS = 6
    MISC_FIRE = 7
    MISC_EXPLOSION = 8
    MISC_LAVA = 9
    MISC_MYSTICAL = 10
    MISC_SMOKE = 11
    MISC_LARGE_SMOKE = 12


@packet(id=109)
class LabTablePacket:
    """For the EDU Chemistry Lab Table block actor."""

    # CloudburstMC's LabTableSerializer writes pos via helper.writeVector3i
    # (three signed varints unconditionally), NOT helper.writeBlockPosition,
    # so no v944 unsigned-Y to signed-Y switch applies here.
    type: LabTablePacketType = field(type=uint8)
    pos: BlockPos
    reaction: LabTableReactionType = field(type=uint8)


class UnlockedRecipesPacketType(IntEnum):
    EMPTY = 0
    INITIALLY_UNLOCKED_RECIPES = 1
    NEWLY_UNLOCKED_RECIPES = 2
    REMOVE_UNLOCKED_RECIPES = 3
    REMOVE_ALL_UNLOCKED_RECIPES = 4


@packet(id=199, since=575)
class UnlockedRecipesPacket:
    """Sent from server to client, for all previously unlocked recipes on load
    and for any newly unlocked recipes during gameplay."""

    # COMPILER_EXTENSION_NEEDED: until v589 the wire form was a single `bool`
    # (true == NEWLY_UNLOCKED_RECIPES, false == INITIALLY_UNLOCKED_RECIPES);
    # since v589 it is a uint32 enum
    packet_type: UnlockedRecipesPacketType = field(type=uint32, since=589)
    unlocked_recipes: list[str]
