from protocol import (
    field,
    int16,
    int32,
    packet,
    uint16,
)
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


class BiomeClimateData:
    temperature: float
    downfall: float
    # bedrock-headers android/r21_u4 (v786) ClimateAttributes carries mRedSporeDensity,
    # mBlueSporeDensity, mAshDensity, mWhiteAshDensity alongside the snow accumulation
    # floats; main (v975) BiomeClimateData has dropped them.
    red_spore_density: float = field(until=844)
    blue_spore_density: float = field(until=844)
    ash_density: float = field(until=844)
    white_ash_density: float = field(until=844)
    snow_accumulation_min: float
    snow_accumulation_max: float


class BiomeDefinitionChunkGenData:
    """Biome chunk-generation parameters. All inner fields reference an external per-packet
    BiomeStringList; codegen for these requires a compiler extension (see packet note)."""

    # COMPILER_EXTENSION_NEEDED: bedrock-headers shows many additional optional members
    # (mConsolidatedFeatures, mMountainParams, mSurfaceMaterialAdjustments, mOverworldGenRules,
    # mMultinoiseGenRules, mLegacyWorldGenRules, mReplaceBiomes, mVillageType, mSurfaceBuilderData,
    # mSubsurfaceBuilderData) whose nested fields encode string members as uint16 indices into the
    # packet-level BiomeStringList. The DSL has no "look this index up in a sibling pool".
    climate: BiomeClimateData | None
    has_default_overworld_surface: bool = field(since=844)
    has_swamp_surface: bool
    has_frozen_ocean_surface: bool
    has_the_end_surface: bool


class BiomeTagsData:
    tags: list[uint16]


class BiomeDefinitionData:
    id: int16  # -1 sentinel means "vanilla, id absent" (writeShortLE branch at v827+)
    temperature: float
    downfall: float
    # bedrock-headers android/r21_u4 (v786) ClimateAttributes confirms the four
    # spore density floats; main (v975) drops them from BiomeDefinitionData.
    red_spore_density: float = field(until=844)
    blue_spore_density: float = field(until=844)
    ash_density: float = field(until=844)
    white_ash_density: float = field(until=844)
    foliage_snow: float = field(since=844)
    depth: float
    scale: float
    map_water_color_argb: int32
    rain: bool
    tag_indices: BiomeTagsData | None
    chunk_gen_data: BiomeDefinitionChunkGenData | None


class BiomeStringList:
    """Deduplicated string pool emitted after the biome definitions; biome-internal string
    fields are stored as uint16 indices into this list."""

    strings: list[str]


@packet(id=122)
class BiomeDefinitionListPacket:
    """On world start, send clients the info for all available biomes."""

    # COMPILER_EXTENSION_NEEDED: each BiomeDefinitionData nested field is written with
    # uint16 indices into the cumulative `string_list` pool that gets emitted only after
    # all entries. Codegen needs cross-field state to thread the same string pool
    # through the nested writes; the map shape itself is expressible as dict[K, V].
    definitions: CompoundTag = field(until=800)
    indexed_definitions: dict[uint16, BiomeDefinitionData] = field(since=800)
    string_list: BiomeStringList = field(since=800)


# CompressedBiomeDefinitionListPacket (id=301, v582..v800) is omitted: it has
# been removed since v800 and the DSL cannot express a lone @packet(until=)
# without a successor declaration. Reintroduce paired with a redeclaration when
# the gating syntax for orphan-until packets lands.
