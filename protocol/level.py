from enum import IntEnum

from protocol import (
    field,
    int8,
    int16,
    int32,
    int64,
    packet,
    type,
    uint16,
    uint32,
    uint64,
    uvarint32,
    varint32,
)
from protocol.common import BlockPos, SubChunkPos, Vec2, Vec3
from protocol.nbt import CompoundTag

package = "bedrock.protocol"

type DimensionType = varint32


class DimensionDefinition:
    name: str
    height_maximum: varint32
    height_minimum: varint32
    generator_type: varint32
    dimension_type: DimensionType = field(since=975)


# TODO: absent from EndstoneMC/protocol-docs r26_u3 (v1001) -- renamed or
# removed after v975. Investigate when bumping past v975 and decide whether
# to add `until=` here or rename the packet to match BDS r26_u3.
@packet(id=180, since=503)
class DimensionDataPacket:
    definitions: list[DimensionDefinition]


@type(since=975)
class ServerSoundHandle:
    value: uint64


@packet(id=86)
class PlaySoundPacket:
    name: str
    pos: BlockPos
    volume: float
    pitch: float
    server_sound_handle: ServerSoundHandle | None = field(since=975)


@packet(id=123, since=332)
class LevelSoundEventPacket:
    """Most sounds get launched on server and replicated to clients, but a handful of player
    initiated sounds are launched on their client and replicated through the network."""

    event_id: uvarint32
    pos: Vec3
    data: varint32
    actor_identifier: str
    is_baby: bool
    is_global: bool
    actor: int64 = field(since=786)
    fire_at_position: Vec3 | None = field(since=975)


@packet(id=56)
class BlockActorDataPacket:
    """Sends the entire user data compound tag and the block position to the client."""

    pos: BlockPos
    data: CompoundTag


class SubChunkPosOffset:
    x: int8
    y: int8
    z: int8


@packet(id=175, since=471)
class SubChunkRequestPacket:
    dimension_type: DimensionType
    center_pos: SubChunkPos
    sub_chunk_pos_offsets: list[SubChunkPosOffset] = field(prefix=uint32, since=486)


# Expression operators used inside biome scatter / element data; the wire form
# is varint32 with -1 representing the absent / unknown op.
type ExpressionOp = varint32


class CoordinateEvaluationOrder(IntEnum):
    XYZ = 0
    XZY = 1
    YXZ = 2
    YZX = 3
    ZXY = 4
    ZYX = 5


class RandomDistributionType(IntEnum):
    SINGLE_VALUED = 0
    UNIFORM = 1
    GAUSSIAN = 2
    INVERSE_GAUSSIAN = 3
    FIXED_GRID = 4
    JITTERED_GRID = 5
    TRIANGLE = 6


class BiomeTemperatureCategory(IntEnum):
    MEDIUM = 0
    WARM = 1
    LUKEWARM = 2
    COLD = 3
    FROZEN = 4


class VillageType(IntEnum):
    DESERT = 0
    ICE = 1
    SAVANNA = 2
    TAIGA = 3
    DEFAULT = 4


class BiomeCoordinateData:
    min_value_type: ExpressionOp
    min_value: uint16
    max_value_type: ExpressionOp
    max_value: uint16
    grid_offset: uint32
    grid_step_size: uint32
    distribution: RandomDistributionType = field(type=varint32)


class BiomeScatterParamData:
    coordinates: list[BiomeCoordinateData]
    eval_order: CoordinateEvaluationOrder = field(type=varint32)
    chance_percent_type: ExpressionOp
    chance_percent: uint16
    chance_numerator: int32
    chance_denominator: int32
    iterations_type: ExpressionOp
    iterations: uint16


class BiomeConsolidatedFeatureData:
    scatter: BiomeScatterParamData
    feature: uint16
    identifier: uint16
    pass_: uint16
    can_use_internal_feature: bool


class BiomeConsolidatedFeaturesData:
    features: list[BiomeConsolidatedFeatureData]


class BiomeClimateData:
    temperature: float
    downfall: float
    snow_accumulation_min: float
    snow_accumulation_max: float


class BiomeMountainParamsData:
    steep_block: uint32
    north_slopes: bool
    south_slopes: bool
    west_slopes: bool
    east_slopes: bool
    top_slide_enabled: bool


class BiomeSurfaceMaterialData:
    top_block: uint32
    mid_block: uint32
    sea_floor_block: uint32
    foundation_block: uint32
    sea_block: uint32
    sea_floor_depth: int32


class BiomeElementData:
    noise_freq_scale: float
    noise_lower_bound: float
    noise_upper_bound: float
    height_min_type: ExpressionOp
    height_min: uint16
    height_max_type: ExpressionOp
    height_max: uint16
    adjusted_materials: BiomeSurfaceMaterialData


class BiomeSurfaceMaterialAdjustmentData:
    adjustments: list[BiomeElementData]


class BiomeWeightedData:
    biome_identifier: uint16
    weight: uint32


class BiomeConditionalTransformationData:
    transforms_into: list[BiomeWeightedData]
    condition_json: uint16
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
    replacement_biome: uint16
    dimension: uint16
    target_biomes: list[uint16]
    amount: float
    noise_frequency_scale: float
    replacement_index: uint32


class BiomeReplacementsData:
    biome_replacements: list[BiomeReplacementData]


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


class BiomeNoiseGradientSurfaceData:
    non_replaceable_blocks: list[uint32]
    gradient_blocks: list[uint32]
    noise_seed_string: str
    first_octave: int32
    amplitudes: list[float]


class BiomeSurfaceBuilderData:
    surface_materials: BiomeSurfaceMaterialData | None
    has_default_overworld_surface: bool
    has_swamp_surface: bool
    has_frozen_ocean_surface: bool
    has_the_end_surface: bool
    mesa_surface: BiomeMesaSurfaceData | None
    capped_surface: BiomeCappedSurfaceData | None
    noise_gradient_surface: BiomeNoiseGradientSurfaceData | None


class BiomeDefinitionChunkGenData:
    climate: BiomeClimateData | None
    consolidated_features: BiomeConsolidatedFeaturesData | None
    mountain_params: BiomeMountainParamsData | None
    surface_material_adjustments: BiomeSurfaceMaterialAdjustmentData | None
    overworld_gen_rules: BiomeOverworldGenRulesData | None
    multinoise_gen_rules: BiomeMultinoiseGenRulesData | None
    legacy_world_gen_rules: BiomeLegacyWorldGenRulesData | None
    replace_biomes: BiomeReplacementsData | None
    village_type: VillageType | None = field(type=int8)
    surface_builder_data: BiomeSurfaceBuilderData | None
    subsurface_builder_data: BiomeSurfaceBuilderData | None


class BiomeTagsData:
    tags: list[uint16]


class BiomeDefinitionData:
    id: int16
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
    strings: list[str]


@packet(id=122)
class BiomeDefinitionListPacket:
    """Sent by the server to tell the client about the biomes that are available."""

    biome_data: dict[uint16, BiomeDefinitionData] = field(prefix=uvarint32)
    string_list: BiomeStringList
