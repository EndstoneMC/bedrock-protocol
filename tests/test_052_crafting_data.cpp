#include <string>

#include "fixture.hpp"

namespace {

bp::SerializedRecipeIngredient_<1001> stick_1001()
{
    bp::SerializedRecipeIngredient_<1001> out;
    out.descriptor.internal_type = bp::ItemDescriptor_<1001>::InternalType::DEFAULT;
    out.descriptor.id = 5;
    out.descriptor.aux_value = 1;
    out.stack_size = 2;
    return out;
}

bp::SerializedNetworkItemInstanceDescriptor_<1001> plank_1001()
{
    bp::SerializedNetworkItemInstanceDescriptor_<1001> out;
    out.id = 7;
    out.stack_size = 4;
    out.aux_value = 0;
    out.block_runtime_id = 9;
    out.user_data_buffer = empty_item_blob();
    return out;
}

bp::SerializedRecipeIngredient_<2168> stick_2168()
{
    bp::SerializedRecipeIngredient_<2168> out;
    out.descriptor.emplace("name", "minecraft:stick");
    out.aux_value = 1;
    out.stack_size = 2;
    return out;
}

bp::SerializedNetworkItemInstanceDescriptor_<2168> plank_2168()
{
    bp::SerializedNetworkItemInstanceDescriptor_<2168> out;
    out.id = 7;
    out.stack_size = 4;
    out.aux_value = 0;
    out.block_runtime_id = 9;
    out.user_data_buffer = empty_item_blob();
    return out;
}

bp::CraftingDataPacket_<1001> fill_1001()
{
    bp::CraftingDataPacket_<1001> pkt;

    bp::CraftingDataEntry_<1001> shaped;
    shaped.entry_type = bp::CraftingDataEntryType::SHAPED_RECIPE;
    shaped.shaped_recipe.recipe_id = "r1";
    shaped.shaped_recipe.width = 1;
    shaped.shaped_recipe.height = 1;
    shaped.shaped_recipe.ingredients = {stick_1001()};
    shaped.shaped_recipe.results = {plank_1001()};
    shaped.shaped_recipe.recipe_uuid = {};
    shaped.shaped_recipe.tag = "crafting_table";
    shaped.shaped_recipe.priority = 3;
    shaped.shaped_recipe.assume_symmetry = true;
    shaped.shaped_recipe.unlocking_requirement.context =
        bp::SerializedRecipeUnlockingRequirement_<1001>::UnlockingContext::ALWAYS_UNLOCKED;
    shaped.shaped_recipe.net_id = {.raw_id = 11};
    pkt.crafting_entries.push_back(shaped);

    bp::CraftingDataEntry_<1001> shapeless;
    shapeless.entry_type = bp::CraftingDataEntryType::SHAPELESS_RECIPE;
    shapeless.shapeless_recipe.recipe_id = "r2";
    shapeless.shapeless_recipe.ingredients = {stick_1001()};
    shapeless.shapeless_recipe.results = {plank_1001()};
    shapeless.shapeless_recipe.recipe_uuid = {};
    shapeless.shapeless_recipe.tag = "crafting_table";
    shapeless.shapeless_recipe.priority = 0;
    shapeless.shapeless_recipe.unlocking_requirement.context =
        bp::SerializedRecipeUnlockingRequirement_<1001>::UnlockingContext::NONE;
    shapeless.shapeless_recipe.unlocking_requirement.ingredients = {stick_1001()};
    shapeless.shapeless_recipe.net_id = {.raw_id = 12};
    pkt.crafting_entries.push_back(shapeless);

    bp::CraftingDataEntry_<1001> multi;
    multi.entry_type = bp::CraftingDataEntryType::MULTI_RECIPE;
    multi.multi_recipe.recipe_uuid = {};
    multi.multi_recipe.net_id = {.raw_id = 13};
    pkt.crafting_entries.push_back(multi);

    bp::CraftingDataEntry_<1001> transform;
    transform.entry_type = bp::CraftingDataEntryType::SMITHING_TRANSFORM_RECIPE;
    transform.smithing_transform_recipe.recipe_id = "r4";
    transform.smithing_transform_recipe.template_ingredient = stick_1001();
    transform.smithing_transform_recipe.base_ingredient = stick_1001();
    transform.smithing_transform_recipe.addition_ingredient = stick_1001();
    transform.smithing_transform_recipe.result = plank_1001();
    transform.smithing_transform_recipe.tag = "smithing_table";
    transform.smithing_transform_recipe.net_id = {.raw_id = 14};
    pkt.crafting_entries.push_back(transform);

    bp::CraftingDataEntry_<1001> trim;
    trim.entry_type = bp::CraftingDataEntryType::SMITHING_TRIM_RECIPE;
    trim.smithing_trim_recipe.recipe_id = "r5";
    trim.smithing_trim_recipe.template_ingredient = stick_1001();
    trim.smithing_trim_recipe.base_ingredient = stick_1001();
    trim.smithing_trim_recipe.addition_ingredient = stick_1001();
    trim.smithing_trim_recipe.tag = "smithing_table";
    trim.smithing_trim_recipe.net_id = {.raw_id = 15};
    pkt.crafting_entries.push_back(trim);

    pkt.potion_mix_entries.push_back({.from_item_id = 1,
                                      .from_item_aux = 2,
                                      .reagent_item_id = 3,
                                      .reagent_item_aux = 4,
                                      .to_item_id = 5,
                                      .to_item_aux = 6});
    pkt.container_mix_entries.push_back({.from_item_id = 7, .reagent_item_id = 8, .to_item_id = 9});
    pkt.material_reducer_entries.push_back(
        {.from_item_key = 20, .to_item_ids_and_counts = {{.item_id = 21, .item_count = 22}}});
    pkt.clear_recipes = true;
    return pkt;
}

bp::CraftingDataPacket_<2168> fill_2168()
{
    bp::CraftingDataPacket_<2168> pkt;

    bp::ShapedRecipePayload_<2168> shaped;
    shaped.recipe_id = "r1";
    shaped.width = 1;
    shaped.height = 1;
    shaped.ingredients = {stick_2168()};
    shaped.results = {plank_2168()};
    shaped.recipe_uuid = {};
    shaped.tag = "crafting_table";
    shaped.priority = 3;
    shaped.assume_symmetry = true;
    shaped.unlocking_requirement = bp::SerializedRecipeUnlockingRequirement_<2168>{
        .context = bp::SerializedRecipeUnlockingRequirement_<2168>::UnlockingContext::ALWAYS_UNLOCKED,
        .ingredients = std::nullopt};
    shaped.net_id = {.raw_id = 11};
    pkt.shaped_recipes.push_back(shaped);

    bp::ShapelessRecipePayload_<2168> shapeless;
    shapeless.recipe_id = "r2";
    shapeless.ingredients = {stick_2168()};
    shapeless.results = {plank_2168()};
    shapeless.recipe_uuid = {};
    shapeless.tag = "crafting_table";
    shapeless.priority = 0;
    shapeless.unlocking_requirement = bp::SerializedRecipeUnlockingRequirement_<2168>{
        .context = bp::SerializedRecipeUnlockingRequirement_<2168>::UnlockingContext::NONE,
        .ingredients = std::vector<bp::SerializedRecipeIngredient_<2168>>{stick_2168()}};
    shapeless.net_id = {.raw_id = 12};
    pkt.shapeless_recipes.push_back(shapeless);

    pkt.multi_recipes.push_back({.recipe_uuid = {}, .net_id = {.raw_id = 13}});

    bp::SmithingTransformRecipePayload_<2168> transform;
    transform.recipe_id = "r4";
    transform.template_ingredient = stick_2168();
    transform.base_ingredient = stick_2168();
    transform.addition_ingredient = stick_2168();
    transform.result = plank_2168();
    transform.tag = "smithing_table";
    transform.net_id = {.raw_id = 14};
    pkt.smithing_transform_recipes.push_back(transform);

    bp::SmithingTrimRecipePayload_<2168> trim;
    trim.recipe_id = "r5";
    trim.template_ingredient = stick_2168();
    trim.base_ingredient = stick_2168();
    trim.addition_ingredient = stick_2168();
    trim.tag = "smithing_table";
    trim.net_id = {.raw_id = 15};
    pkt.smithing_trim_recipes.push_back(trim);

    pkt.potion_mixes.push_back({.from_item_id = 1,
                                .from_item_aux = 2,
                                .reagent_item_id = 3,
                                .reagent_item_aux = 4,
                                .to_item_id = 5,
                                .to_item_aux = 6});
    pkt.container_mixes.push_back({.from_item_id = 7, .reagent_item_id = 8, .to_item_id = 9});
    pkt.material_reducers.push_back(
        {.from_item_key = 20, .to_item_ids_and_counts = {{.item_id = 21, .item_count = 22}}});
    pkt.clear_recipes = true;
    return pkt;
}

}  // namespace

TEST_CASE("CraftingDataPacket: id")
{
    STATIC_REQUIRE(bp::CraftingDataPacket_<975>::Id == 52);
    STATIC_REQUIRE(bp::CraftingDataPacket_<1001>::Id == 52);
    STATIC_REQUIRE(bp::CraftingDataPacket_<2168>::Id == 52);
}

TEST_CASE("CraftingDataPacket: v1001 round-trip")
{
    using Packet = bp::CraftingDataPacket_<1001>;

    const Packet pkt = fill_1001();

    // generated by gophertunnel:
    // packet.CraftingData{
    //   Recipes: []protocol.Recipe{
    //     &protocol.ShapedRecipe{RecipeID: "r1", Width: 1, Height: 1,
    //       Input: []protocol.ItemDescriptorCount{{Descriptor: &protocol.DefaultItemDescriptor{
    //         NetworkID: 5, MetadataValue: 1}, Count: 2}},
    //       Output: []protocol.ItemStack{{ItemType: protocol.ItemType{NetworkID: 7},
    //         Count: 4, BlockRuntimeID: 9}},
    //       Block: "crafting_table", Priority: 3, AssumeSymmetry: true,
    //       UnlockRequirement: protocol.RecipeUnlockRequirement{
    //         Context: protocol.RecipeUnlockContextAlwaysUnlocked},
    //       RecipeNetworkID: 11},
    //     &protocol.ShapelessRecipe{RecipeID: "r2", Input: <same>, Output: <same>,
    //       Block: "crafting_table", Priority: 0,
    //       UnlockRequirement: protocol.RecipeUnlockRequirement{
    //         Context: protocol.RecipeUnlockContextNone, Ingredients: <same>},
    //       RecipeNetworkID: 12},
    //     &protocol.MultiRecipe{RecipeNetworkID: 13},
    //     &protocol.SmithingTransformRecipe{RecipeNetworkID: 14, RecipeID: "r4",
    //       Template: <same>, Base: <same>, Addition: <same>, Result: <same>,
    //       Block: "smithing_table"},
    //     &protocol.SmithingTrimRecipe{RecipeNetworkID: 15, RecipeID: "r5",
    //       Template: <same>, Base: <same>, Addition: <same>, Block: "smithing_table"}},
    //   PotionRecipes: []protocol.PotionRecipe{{InputPotionID: 1, InputPotionMetadata: 2,
    //     ReagentItemID: 3, ReagentItemMetadata: 4, OutputPotionID: 5, OutputPotionMetadata: 6}},
    //   PotionContainerChangeRecipes: []protocol.PotionContainerChangeRecipe{{
    //     InputItemID: 7, ReagentItemID: 8, OutputItemID: 9}},
    //   MaterialReducers: []protocol.MaterialReducer{{
    //     InputItem: protocol.ItemType{MetadataValue: 20},
    //     Outputs: []protocol.MaterialReducerOutput{{NetworkID: 21, Count: 22}}}},
    //   ClearRecipes: true}
    const std::string golden = bytes({
    0x05, 0x02, 0x02, 0x72, 0x31, 0x02, 0x02, 0x01, 0x05, 0x00, 0x01, 0x00,
    0x04, 0x01, 0x0E, 0x04, 0x00, 0x00, 0x12, 0x0A, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0E, 0x63,
    0x72, 0x61, 0x66, 0x74, 0x69, 0x6E, 0x67, 0x5F, 0x74, 0x61, 0x62, 0x6C,
    0x65, 0x06, 0x01, 0x01, 0x0B, 0x00, 0x02, 0x72, 0x32, 0x01, 0x01, 0x05,
    0x00, 0x01, 0x00, 0x04, 0x01, 0x0E, 0x04, 0x00, 0x00, 0x12, 0x0A, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x0E, 0x63, 0x72, 0x61, 0x66, 0x74, 0x69, 0x6E, 0x67, 0x5F, 0x74,
    0x61, 0x62, 0x6C, 0x65, 0x00, 0x00, 0x01, 0x01, 0x05, 0x00, 0x01, 0x00,
    0x04, 0x0C, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0D, 0x10, 0x02, 0x72, 0x34,
    0x01, 0x05, 0x00, 0x01, 0x00, 0x04, 0x01, 0x05, 0x00, 0x01, 0x00, 0x04,
    0x01, 0x05, 0x00, 0x01, 0x00, 0x04, 0x0E, 0x04, 0x00, 0x00, 0x12, 0x0A,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0E, 0x73,
    0x6D, 0x69, 0x74, 0x68, 0x69, 0x6E, 0x67, 0x5F, 0x74, 0x61, 0x62, 0x6C,
    0x65, 0x0E, 0x12, 0x02, 0x72, 0x35, 0x01, 0x05, 0x00, 0x01, 0x00, 0x04,
    0x01, 0x05, 0x00, 0x01, 0x00, 0x04, 0x01, 0x05, 0x00, 0x01, 0x00, 0x04,
    0x0E, 0x73, 0x6D, 0x69, 0x74, 0x68, 0x69, 0x6E, 0x67, 0x5F, 0x74, 0x61,
    0x62, 0x6C, 0x65, 0x0F, 0x01, 0x02, 0x04, 0x06, 0x08, 0x0A, 0x0C, 0x01,
    0x0E, 0x10, 0x12, 0x01, 0x28, 0x01, 0x2A, 0x2C, 0x01,
});

    REQUIRE(encode(pkt) == golden);

    const auto rt = decode<Packet>(golden);
    REQUIRE(rt.crafting_entries.size() == 5);
    REQUIRE(rt.crafting_entries[0].entry_type == bp::CraftingDataEntryType::SHAPED_RECIPE);
    REQUIRE(rt.crafting_entries[0].shaped_recipe.ingredients.size() == 1);
    REQUIRE(rt.crafting_entries[1].shapeless_recipe.unlocking_requirement.ingredients.size() == 1);
    REQUIRE(rt.crafting_entries[2].multi_recipe.net_id.raw_id == 13);
    REQUIRE(rt.material_reducer_entries[0].to_item_ids_and_counts[0].item_count == 22);
    REQUIRE(rt.clear_recipes);
}

TEST_CASE("CraftingDataPacket: v2168 round-trip")
{
    using Packet = bp::CraftingDataPacket_<2168>;

    const Packet pkt = fill_2168();

    // generated by CloudburstMC Bedrock_v2168:
    // CraftingDataPacket{
    //   shapedData: [ShapedRecipeData.of(SHAPED, "r1", 1, 1,
    //     [ItemDescriptorWithCount(DefaultDescriptor(SimpleItemDefinition("minecraft:stick", 5), 1), 2)],
    //     [ItemData(SimpleItemDefinition("minecraft:planks", 7), damage 0, count 4,
    //       SimpleBlockDefinition("minecraft:planks", 9))],
    //     UUID(0, 0), "crafting_table", 3, 11, true,
    //     RecipeUnlockingRequirement(ALWAYS_UNLOCKED))],
    //   shapelessData: [ShapelessRecipeData.of(SHAPELESS, "r2", <same>, <same>, UUID(0, 0),
    //     "crafting_table", 0, 12, RecipeUnlockingRequirement(NONE) + 1 ingredient)],
    //   multiData: [MultiRecipeData.of(UUID(0, 0), 13)],
    //   smithingTransformData: [SmithingTransformRecipeData.of("r4", <same>, <same>, <same>,
    //     <same>, "smithing_table", 14)],
    //   smithingTrimData: [SmithingTrimRecipeData.of("r5", <same>, <same>, <same>,
    //     "smithing_table", 15)],
    //   potionMixData: [PotionMixData(1, 2, 3, 4, 5, 6)],
    //   containerMixData: [ContainerMixData(7, 8, 9)],
    //   materialReducers: [MaterialReducer(20, {SimpleItemDefinition("minecraft:out", 21): 22})],
    //   cleanRecipes: true}
    const std::string golden = bytes({
    0x01, 0x02, 0x72, 0x31, 0x02, 0x02, 0x01, 0x01, 0x04, 0x6E, 0x61, 0x6D,
    0x65, 0x0F, 0x6D, 0x69, 0x6E, 0x65, 0x63, 0x72, 0x61, 0x66, 0x74, 0x3A,
    0x73, 0x74, 0x69, 0x63, 0x6B, 0x02, 0x04, 0x01, 0x0E, 0x04, 0x00, 0x00,
    0x12, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x0E, 0x63, 0x72, 0x61, 0x66, 0x74, 0x69, 0x6E,
    0x67, 0x5F, 0x74, 0x61, 0x62, 0x6C, 0x65, 0x06, 0x01, 0x01, 0x02, 0x00,
    0x0B, 0x01, 0x02, 0x72, 0x32, 0x01, 0x01, 0x04, 0x6E, 0x61, 0x6D, 0x65,
    0x0F, 0x6D, 0x69, 0x6E, 0x65, 0x63, 0x72, 0x61, 0x66, 0x74, 0x3A, 0x73,
    0x74, 0x69, 0x63, 0x6B, 0x02, 0x04, 0x01, 0x0E, 0x04, 0x00, 0x00, 0x12,
    0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x0E, 0x63, 0x72, 0x61, 0x66, 0x74, 0x69, 0x6E, 0x67,
    0x5F, 0x74, 0x61, 0x62, 0x6C, 0x65, 0x00, 0x01, 0x00, 0x01, 0x01, 0x01,
    0x04, 0x6E, 0x61, 0x6D, 0x65, 0x0F, 0x6D, 0x69, 0x6E, 0x65, 0x63, 0x72,
    0x61, 0x66, 0x74, 0x3A, 0x73, 0x74, 0x69, 0x63, 0x6B, 0x02, 0x04, 0x0C,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x0D, 0x00, 0x00, 0x00, 0x01, 0x02, 0x72,
    0x34, 0x01, 0x04, 0x6E, 0x61, 0x6D, 0x65, 0x0F, 0x6D, 0x69, 0x6E, 0x65,
    0x63, 0x72, 0x61, 0x66, 0x74, 0x3A, 0x73, 0x74, 0x69, 0x63, 0x6B, 0x02,
    0x04, 0x01, 0x04, 0x6E, 0x61, 0x6D, 0x65, 0x0F, 0x6D, 0x69, 0x6E, 0x65,
    0x63, 0x72, 0x61, 0x66, 0x74, 0x3A, 0x73, 0x74, 0x69, 0x63, 0x6B, 0x02,
    0x04, 0x01, 0x04, 0x6E, 0x61, 0x6D, 0x65, 0x0F, 0x6D, 0x69, 0x6E, 0x65,
    0x63, 0x72, 0x61, 0x66, 0x74, 0x3A, 0x73, 0x74, 0x69, 0x63, 0x6B, 0x02,
    0x04, 0x0E, 0x04, 0x00, 0x00, 0x12, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x0E, 0x73, 0x6D, 0x69, 0x74, 0x68, 0x69,
    0x6E, 0x67, 0x5F, 0x74, 0x61, 0x62, 0x6C, 0x65, 0x0E, 0x01, 0x02, 0x72,
    0x35, 0x01, 0x04, 0x6E, 0x61, 0x6D, 0x65, 0x0F, 0x6D, 0x69, 0x6E, 0x65,
    0x63, 0x72, 0x61, 0x66, 0x74, 0x3A, 0x73, 0x74, 0x69, 0x63, 0x6B, 0x02,
    0x04, 0x01, 0x04, 0x6E, 0x61, 0x6D, 0x65, 0x0F, 0x6D, 0x69, 0x6E, 0x65,
    0x63, 0x72, 0x61, 0x66, 0x74, 0x3A, 0x73, 0x74, 0x69, 0x63, 0x6B, 0x02,
    0x04, 0x01, 0x04, 0x6E, 0x61, 0x6D, 0x65, 0x0F, 0x6D, 0x69, 0x6E, 0x65,
    0x63, 0x72, 0x61, 0x66, 0x74, 0x3A, 0x73, 0x74, 0x69, 0x63, 0x6B, 0x02,
    0x04, 0x0E, 0x73, 0x6D, 0x69, 0x74, 0x68, 0x69, 0x6E, 0x67, 0x5F, 0x74,
    0x61, 0x62, 0x6C, 0x65, 0x0F, 0x01, 0x02, 0x04, 0x06, 0x08, 0x0A, 0x0C,
    0x01, 0x0E, 0x10, 0x12, 0x01, 0x28, 0x01, 0x2A, 0x2C, 0x01,
});

    REQUIRE(encode(pkt) == golden);

    const auto rt = decode<Packet>(golden);
    REQUIRE(rt.shaped_recipes.size() == 1);
    REQUIRE(rt.shaped_recipes[0].ingredients[0].descriptor.at("name") == "minecraft:stick");
    REQUIRE(rt.shaped_recipes[0].unlocking_requirement.has_value());
    REQUIRE(!rt.shaped_recipes[0].unlocking_requirement->ingredients.has_value());
    REQUIRE(rt.shapeless_recipes[0].unlocking_requirement->ingredients->size() == 1);
    REQUIRE(rt.user_data_shapeless_recipes.empty());
    REQUIRE(rt.shapeless_chemistry_recipes.empty());
    REQUIRE(rt.shaped_chemistry_recipes.empty());
    REQUIRE(rt.multi_recipes[0].net_id.raw_id == 13);
    REQUIRE(rt.clear_recipes);
}

// One polymorphic tagged list became eleven typed ones, so an empty packet grows from
// four length prefixes plus the flag to eleven plus the flag: the eras cannot even
// agree on the shape of nothing.
TEST_CASE("CraftingDataPacket: an empty body is four counts at v1001 and eleven at v2168")
{
    const auto old_empty = encode(bp::CraftingDataPacket_<1001>{});
    const auto new_empty = encode(bp::CraftingDataPacket_<2168>{});

    REQUIRE(old_empty.size() == 5);
    REQUIRE(new_empty.size() == 12);

    REQUIRE(rejects<bp::CraftingDataPacket_<2168>>(old_empty));
    REQUIRE(decode_partial<bp::CraftingDataPacket_<1001>>(new_empty).crafting_entries.empty());
}
