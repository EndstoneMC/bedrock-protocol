"""Biome definitions as serialized to the client: world/level/biome/serialization/."""

from enum import IntEnum, auto

from protocol import field, int32, packet, type, uint8, uint16, uint32, value, varint32
from protocol.molang import ExpressionOp

package = "bedrock.protocol"


type BiomeStringIndex = uint16


class VillageType(IntEnum, uint8):
    DESERT = 0
    ICE = 1
    SAVANNA = 2
    TAIGA = 3
    DEFAULT = 4


class BiomeTemperatureCategory(IntEnum, uint8):
    MEDIUM = 0
    WARM = 1
    LUKEWARM = 2
    COLD = 3
    FROZEN = 4
    COUNT = auto()


class CoordinateEvaluationOrder(IntEnum):
    XYZ = value(0, cpp_name="XYZ")
    XZY = value(1, cpp_name="XZY")
    YXZ = value(2, cpp_name="YXZ")
    YZX = value(3, cpp_name="YZX")
    ZXY = value(4, cpp_name="ZXY")
    ZYX = value(5, cpp_name="ZYX")


class RandomDistributionType(IntEnum):
    SINGLE_VALUED = 0
    UNIFORM = 1
    GAUSSIAN = 2
    INVERSE_GAUSSIAN = 3
    FIXED_GRID = 4
    JITTERED_GRID = 5
    TRIANGLE = 6


class FloatRange:
    min: float
    max: float


@type(since=1001)
class NoiseDescriptor:
    name: str
    first_octave: int32
    amplitudes: list[float]


@type(since=1001)
class SerializedNoiseBlockSpecifier:
    noise: str
    threshold: float
    range: FloatRange
    block_runtime_id: uint32


@type(until=1001)
class BiomeNoiseGradientSurfaceData:
    non_replaceable_blocks: list[uint32]
    gradient_blocks: list[uint32]
    noise_seed_string: str
    first_octave: int32
    amplitudes: list[float]


@type(since=1001)
class BiomeNoiseGradientSurfaceData:
    non_replaceable_blocks: list[uint32]
    gradient_block_ranges: list[SerializedNoiseBlockSpecifier]
    noise_descriptor: NoiseDescriptor


class BiomeSurfaceMaterialData:
    top_block: uint32
    mid_block: uint32
    sea_floor_block: uint32
    foundation_block: uint32
    sea_block: uint32
    sea_floor_depth: int32


class BiomeMesaSurfaceData:
    clay_material: uint32
    hard_clay_material: uint32
    bryce_pillars: bool
    has_forest: bool


class BiomeCappedSurfaceData:
    floor_blocks: list[uint32]
    ceiling_blocks: list[uint32]
    sea_block: uint32 | None
    foundation_block: uint32 | None
    beach_block: uint32 | None


class BiomeSurfaceBuilderData:
    surface_materials: BiomeSurfaceMaterialData | None
    has_default_overworld_surface: bool
    has_swamp_surface: bool
    has_frozen_ocean_surface: bool
    has_the_end_surface: bool
    mesa_surface: BiomeMesaSurfaceData | None
    capped_surface: BiomeCappedSurfaceData | None
    noise_gradient_surface: BiomeNoiseGradientSurfaceData | None


class BiomeClimateData:
    temperature: float
    downfall: float
    red_spore_density: float = field(until=844)
    blue_spore_density: float = field(until=844)
    ash_density: float = field(until=844)
    white_ash_density: float = field(until=844)
    snow_accumulation_min: float
    snow_accumulation_max: float


class BiomeCoordinateData:
    min_value_type: ExpressionOp = field(type=varint32)
    min_value: BiomeStringIndex
    max_value_type: ExpressionOp = field(type=varint32)
    max_value: BiomeStringIndex
    grid_offset: uint32
    grid_step_size: uint32
    distribution: RandomDistributionType


class BiomeScatterParamData:
    coordinates: list[BiomeCoordinateData]
    eval_order: CoordinateEvaluationOrder
    chance_percent_type: ExpressionOp = field(type=varint32)
    chance_percent: BiomeStringIndex
    chance_numerator: int32
    chance_denominator: int32
    iterations_type: ExpressionOp = field(type=varint32)
    iterations: BiomeStringIndex


class BiomeConsolidatedFeatureData:
    scatter: BiomeScatterParamData
    feature: BiomeStringIndex
    identifier: BiomeStringIndex
    pass_: BiomeStringIndex
    can_use_internal_feature: bool


class BiomeConsolidatedFeaturesData:
    features: list[BiomeConsolidatedFeatureData]


class BiomeMountainParamsData:
    steep_block: uint32
    north_slopes: bool
    south_slopes: bool
    west_slopes: bool
    east_slopes: bool
    top_slide_enabled: bool


class BiomeElementData:
    noise_freq_scale: float
    noise_lower_bound: float
    noise_upper_bound: float
    height_min_type: ExpressionOp = field(type=varint32)
    height_min: BiomeStringIndex
    height_max_type: ExpressionOp = field(type=varint32)
    height_max: BiomeStringIndex
    adjusted_materials: BiomeSurfaceMaterialData


class BiomeSurfaceMaterialAdjustmentData:
    adjustments: list[BiomeElementData]


class BiomeWeightedData:
    biome_identifier: BiomeStringIndex
    weight: uint32


class BiomeConditionalTransformationData:
    transforms_into: list[BiomeWeightedData]
    condition_json: BiomeStringIndex
    min_passing_neighbors: uint32


class BiomeWeightedTemperatureData:
    temperature: BiomeTemperatureCategory = field(type=varint32)
    weight: uint32


class BiomeOverworldGenRulesData:
    hills_transformations: list[BiomeWeightedData]
    mutate_transformations: list[BiomeWeightedData]
    river_transformations: list[BiomeWeightedData]
    shore_transformations: list[BiomeWeightedData]
    pre_hills_edge: list[BiomeConditionalTransformationData]
    post_shore_edge: list[BiomeConditionalTransformationData]
    climate: list[BiomeWeightedTemperatureData]


class BiomeMultinoiseGenRulesData:
    temperature: float
    humidity: float
    altitude: float
    weirdness: float
    weight: float


class BiomeLegacyWorldGenRulesData:
    legacy_pre_hills_edge: list[BiomeConditionalTransformationData]


class BiomeReplacementData:
    replacement_biome: BiomeStringIndex
    dimension: BiomeStringIndex
    target_biomes: list[uint16]
    amount: float
    noise_frequency_scale: float
    replacement_index: uint32


class BiomeReplacementsData:
    biome_replacements: list[BiomeReplacementData]


class BiomeTagsData:
    tags: list[uint16]


class BiomeDefinitionChunkGenData:
    climate: BiomeClimateData | None
    consolidated_features: BiomeConsolidatedFeaturesData | None
    mountain_params: BiomeMountainParamsData | None
    surface_material_adjustments: BiomeSurfaceMaterialAdjustmentData | None
    surface_materials: BiomeSurfaceMaterialData | None = field(until=975)
    has_default_overworld_surface: bool = field(since=844, until=975)
    has_swamp_surface: bool = field(until=975)
    has_frozen_ocean_surface: bool = field(until=975)
    has_the_end_surface: bool = field(until=975)
    mesa_surface: BiomeMesaSurfaceData | None = field(until=975)
    capped_surface: BiomeCappedSurfaceData | None = field(until=975)
    overworld_gen_rules: BiomeOverworldGenRulesData | None
    multinoise_gen_rules: BiomeMultinoiseGenRulesData | None
    legacy_world_gen_rules: BiomeLegacyWorldGenRulesData | None
    replace_biomes: BiomeReplacementsData | None = field(since=859)
    village_type: VillageType | None = field(type=uint8, since=924)
    surface_builder_data: BiomeSurfaceBuilderData | None = field(since=975)
    subsurface_builder_data: BiomeSurfaceBuilderData | None = field(since=975)


class BiomeDefinitionData:
    id: uint16
    temperature: float
    downfall: float
    red_spore_density: float = field(until=844)
    blue_spore_density: float = field(until=844)
    ash_density: float = field(until=844)
    white_ash_density: float = field(until=844)
    foliage_snow: float = field(since=844)
    depth: float
    scale: float
    map_water_color_argb: int32
    rain: bool
    tags: BiomeTagsData | None
    chunk_gen_data: BiomeDefinitionChunkGenData | None


class BiomeStringList:
    strings: list[str]


@packet(id=122)
class BiomeDefinitionListPacket:
    biome_data: dict[BiomeStringIndex, BiomeDefinitionData]
    string_list: BiomeStringList
