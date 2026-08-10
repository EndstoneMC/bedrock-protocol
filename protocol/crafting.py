import uuid
from enum import IntEnum, auto

from protocol import field, int16, int32, packet, type, uint8, uint16, uvarint32, varint32

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


class CraftingDataEntryType(IntEnum, int):
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
        when=lambda d: d.internal_type
        in {
            InternalType.MOLANG,
            InternalType.ITEM_TAG,
            InternalType.DEFERRED,
            InternalType.COMPLEX_ALIAS,
        }
    )
    molang_version: uint8 = field(when=lambda d: d.internal_type == InternalType.MOLANG)
    aux_value: int16 = field(
        when=lambda d: d.internal_type == InternalType.DEFERRED
        or (d.internal_type == InternalType.DEFAULT and d.id != 0)
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
    class UnlockingContext(IntEnum, int):
        NONE = 0
        ALWAYS_UNLOCKED = 1
        PLAYER_IN_WATER = 2
        PLAYER_HAS_MANY_ITEMS = 3

    context: UnlockingContext = field(type=uint8)
    ingredients: list[SerializedRecipeIngredient] = field(when=lambda r: r.context == UnlockingContext.NONE)


@type(since=2168)
class SerializedRecipeUnlockingRequirement:
    class UnlockingContext(IntEnum, int):
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
        when=lambda e: e.entry_type
        in {
            CraftingDataEntryType.SHAPELESS_RECIPE,
            CraftingDataEntryType.USER_DATA_SHAPELESS_RECIPE,
        }
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
