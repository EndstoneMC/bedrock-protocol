from enum import IntEnum, auto

from protocol import field, int32, packet, type, uint8, uint16, uint32, varint32
from protocol.molang import ExpressionOp

package = "bedrock.protocol"


# BDS BiomeStringList::BiomeStringIndex -- an index into the packet's string pool.
type BiomeStringIndex = uint16


# BDS: SharedTypes::VillageType.
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


# BDS: SharedTypes::v1_21_10::CoordinateEvaluationOrder.
class CoordinateEvaluationOrder(IntEnum, int):
    XYZ = 0
    XZY = 1
    YXZ = 2
    YZX = 3
    ZXY = 4
    ZYX = 5


# BDS: SharedTypes::v1_21_10::RandomDistributionType.
class RandomDistributionType(IntEnum, int):
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
    # uint8 underlying would derive uint8; cereal compresses this one.
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
    overworld_gen_rules: BiomeOverworldGenRulesData | None
    multinoise_gen_rules: BiomeMultinoiseGenRulesData | None
    legacy_world_gen_rules: BiomeLegacyWorldGenRulesData | None
    replace_biomes: BiomeReplacementsData | None
    village_type: VillageType | None = field(type=uint8)
    surface_builder_data: BiomeSurfaceBuilderData | None
    subsurface_builder_data: BiomeSurfaceBuilderData | None


class BiomeDefinitionData:
    id: uint16
    temperature: float
    downfall: float
    foliage_snow: float
    depth: float
    scale: float
    map_water_color_argb: int32
    rain: bool
    tags: BiomeTagsData | None
    chunk_gen_data: BiomeDefinitionChunkGenData | None


class BiomeStringList:
    # BDS also carries mAllStrings, the reverse index; only mStrings is on the wire.
    strings: list[str]


# Cerealised at 975, the floor snapshot, so no pre-cereal shape is left to gate.
@packet(id=122)
class BiomeDefinitionListPacket:
    biome_data: dict[BiomeStringIndex, BiomeDefinitionData]
    string_list: BiomeStringList
