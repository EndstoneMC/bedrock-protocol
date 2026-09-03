"""Recipes and their registries: world/item/crafting/, world/item/enchanting/ and
world/item/alchemy/ -- recipe payloads, potion and container mixes, material reduction,
the lab table, enchant options."""

import uuid
from enum import IntEnum, auto

from protocol import array, field, int16, int32, packet, type, uint8, uint16, uint32, uvarint32, varint32
from protocol.common import BlockPos

package = "bedrock.protocol"


class CreativeItemCategory(IntEnum, uint8):
    ALL = 0
    CONSTRUCTION = 1
    NATURE = 2
    EQUIPMENT = 3
    ITEMS = 4
    ITEM_COMMAND_ONLY = 5
    UNDEFINED = 6
    NUM_CATEGORIES = auto()


class CraftingDataEntryType(IntEnum):
    SHAPELESS_RECIPE = 0
    SHAPED_RECIPE = 1
    MULTI_RECIPE = 4
    USER_DATA_SHAPELESS_RECIPE = 5
    SHAPELESS_CHEMISTRY_RECIPE = 6
    SHAPED_CHEMISTRY_RECIPE = 7
    SMITHING_TRANSFORM_RECIPE = 8
    SMITHING_TRIM_RECIPE = 9
    COUNT = auto()


class RecipeNetId:
    raw_id: uvarint32


class CreativeItemNetId:
    raw_id: uvarint32


@type(until=2168)
class SerializedNetworkItemInstanceDescriptor:
    """NetworkItemInstanceDescriptor::write. An air item (id 0) is a lone zero
    byte: the write returns early, so nothing else reaches the wire."""

    id: varint32

    with field(when=lambda d: d.id != 0):
        stack_size: uint16
        aux_value: uvarint32
        block_runtime_id: varint32
        user_data_buffer: bytes


@type(since=2168)
class SerializedNetworkItemInstanceDescriptor:
    """cerealizer<NetworkItemInstanceDescriptor>::SerializedData. The extra data
    (NBT, can-place-on / can-break) rides in a single length-prefixed blob, so it
    stays opaque here -- an empty blob is a lone uvarint32 zero, which is
    byte-identical to BDS's air-item early-out."""

    id: varint32
    stack_size: uint16
    aux_value: uvarint32
    block_runtime_id: varint32
    user_data_buffer: bytes


@type(until=2168)
class ItemDescriptor:
    """ItemDescriptor::serialize. The type byte selects which impl follows; four
    of the six lead with a string, so one slot carries the molang expression,
    the item tag, and the deferred / complex-alias name alike."""

    class InternalType(IntEnum, uint8):
        INVALID = 0
        DEFAULT = 1
        MOLANG = 2
        ITEM_TAG = 3
        DEFERRED = 4
        COMPLEX_ALIAS = 5

    internal_type: InternalType
    id: int16 = field(when=lambda d: d.internal_type == InternalType.DEFAULT)
    name: str = field(
        when=lambda d: (
            d.internal_type
            in {
                InternalType.MOLANG,
                InternalType.ITEM_TAG,
                InternalType.DEFERRED,
                InternalType.COMPLEX_ALIAS,
            }
        )
    )
    molang_version: uint8 = field(when=lambda d: d.internal_type == InternalType.MOLANG)
    aux_value: int16 = field(
        when=lambda d: (
            d.internal_type == InternalType.DEFERRED or (d.internal_type == InternalType.DEFAULT and d.id != 0)
        )
    )


@type(until=2168)
class SerializedRecipeIngredient:
    descriptor: ItemDescriptor
    stack_size: uint16 = field(type=varint32)


@type(since=2168)
class SerializedRecipeIngredient:
    """cerealizer<RecipeIngredient>::SerializedData. The descriptor collapses to
    the impl's toMap(), so the type tag is gone and the case is read back from
    the single key the map carries."""

    descriptor: dict[str, str]
    aux_value: int16 = field(type=varint32)
    stack_size: uint16 = field(type=varint32)


@type(until=2168)
class SerializedRecipeUnlockingRequirement:
    class UnlockingContext(IntEnum):
        NONE = 0
        ALWAYS_UNLOCKED = 1
        PLAYER_IN_WATER = 2
        PLAYER_HAS_MANY_ITEMS = 3

    context: UnlockingContext = field(type=uint8)
    ingredients: list[SerializedRecipeIngredient] = field(when=lambda r: r.context == UnlockingContext.NONE)


@type(since=2168)
class SerializedRecipeUnlockingRequirement:
    class UnlockingContext(IntEnum):
        NONE = 0
        ALWAYS_UNLOCKED = 1
        PLAYER_IN_WATER = 2
        PLAYER_HAS_MANY_ITEMS = 3

    context: UnlockingContext
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
    assume_symmetry: bool
    unlocking_requirement: SerializedRecipeUnlockingRequirement
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
class ShapedChemistryRecipePayload:
    recipe_id: str
    width: varint32
    height: varint32
    ingredients: list[SerializedRecipeIngredient] = field(count=lambda r: r.width * r.height)
    results: list[SerializedNetworkItemInstanceDescriptor]
    uuid: uuid.UUID
    tag: str
    priority: varint32
    assume_symmetry: bool
    net_id: RecipeNetId


@type(until=2168)
class ShapelessRecipePayload:
    recipe_id: str
    ingredients: list[SerializedRecipeIngredient]
    results: list[SerializedNetworkItemInstanceDescriptor]
    uuid: uuid.UUID
    tag: str
    priority: varint32
    unlocking_requirement: SerializedRecipeUnlockingRequirement
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


@type(until=2168)
class ShapelessChemistryRecipePayload:
    recipe_id: str
    ingredients: list[SerializedRecipeIngredient]
    results: list[SerializedNetworkItemInstanceDescriptor]
    uuid: uuid.UUID
    tag: str
    priority: varint32
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


@type(until=2168)
class CraftingDataEntry:
    entry_type: CraftingDataEntryType
    shapeless_recipe: ShapelessRecipePayload = field(
        when=lambda e: (
            e.entry_type
            in {
                CraftingDataEntryType.SHAPELESS_RECIPE,
                CraftingDataEntryType.USER_DATA_SHAPELESS_RECIPE,
            }
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


@type(until=2168)
class CreativeGroupInfoPayload:
    creative_item_category: CreativeItemCategory = field(type=int32)
    name: str
    icon: SerializedNetworkItemInstanceDescriptor


@type(since=2168)
class CreativeGroupInfoPayload:
    creative_item_category: CreativeItemCategory
    name: str
    icon: SerializedNetworkItemInstanceDescriptor


class CreativeItemEntryPayload:
    creative_item_net_id: CreativeItemNetId
    item_descriptor: SerializedNetworkItemInstanceDescriptor
    group_index: uvarint32


@packet(id=145)
class CreativeContentPacket:
    groups: list[CreativeGroupInfoPayload]
    entries: list[CreativeItemEntryPayload]


class LabTableReactionType(IntEnum, uint8):
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


@packet(id=109, since=2168)
class LabTablePacket:
    class Type(IntEnum, uint8):
        START_COMBINE = 0
        START_REACTION = 1
        RESET = 2

    type: Type
    pos: BlockPos
    reaction: LabTableReactionType


class Enchant:
    class Type(IntEnum, uint8):
        PROTECTION = 0
        FIRE_PROTECTION = 1
        FEATHER_FALLING = 2
        BLAST_PROTECTION = 3
        PROJECTILE_PROTECTION = 4
        THORNS = 5
        RESPIRATION = 6
        DEPTH_STRIDER = 7
        AQUA_AFFINITY = 8
        SHARPNESS = 9
        SMITE = 10
        BANE_OF_ARTHROPODS = 11
        KNOCKBACK = 12
        FIRE_ASPECT = 13
        LOOTING = 14
        EFFICIENCY = 15
        SILK_TOUCH = 16
        UNBREAKING = 17
        FORTUNE = 18
        POWER = 19
        PUNCH = 20
        FLAME = 21
        INFINITY = 22
        LUCK_OF_THE_SEA = 23
        LURE = 24
        FROST_WALKER = 25
        MENDING = 26
        CURSE_OF_BINDING = 27
        CURSE_OF_VANISHING = 28
        IMPALING = 29
        RIPTIDE = 30
        LOYALTY = 31
        CHANNELING = 32
        MULTISHOT = 33
        PIERCING = 34
        QUICK_CHARGE = 35
        SOUL_SPEED = 36
        SWIFT_SNEAK = 37
        WIND_BURST = 38
        DENSITY = 39
        BREACH = 40
        LUNGE = 41
        NUM_ENCHANTMENTS = auto()
        INVALID_ENCHANTMENT = 43


class EnchantmentInstance:
    enchant_type: Enchant.Type
    level: uint8


class ItemEnchants:
    slot: int32
    item_enchants: array[list[EnchantmentInstance], 3]


class ItemEnchantOption:
    cost: uint8
    enchants: ItemEnchants
    enchant_name: str
    enchant_net_id: RecipeNetId


@packet(id=146, since=2168)
class PlayerEnchantOptionsPacket:
    options: list[ItemEnchantOption]


@packet(id=199, since=2168)
class UnlockedRecipesPacket:
    class PacketType(IntEnum, uint32):
        EMPTY = 0
        INITIALLY_UNLOCKED_RECIPES = 1
        NEWLY_UNLOCKED_RECIPES = 2
        REMOVE_UNLOCKED_RECIPES = 3
        REMOVE_ALL_UNLOCKED_RECIPES = 4

    packet_type: PacketType = field(type=uint32)
    unlocked_recipes: list[str]
