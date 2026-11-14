"""What the client reports for diagnosis: profile/ Whisker scopes, memory categories,
frame and system timings, plus debug/ markers and the editor channel."""

from enum import IntEnum, auto

from protocol import field, packet, sentinel, type, uint8, uint64, value
from protocol.actor import ActorUniqueID
from protocol.common import Color, Vec3
from protocol.nbt import CompoundTag

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"


class MemoryCategory(IntEnum, uint8):
    UNKNOWN = 0
    INVALID_SIZE_UNKNOWN = 1
    ACTOR = 2
    ACTOR_ANIMATION = 3
    ACTOR_RENDERING = 4
    BALANCER = value(until=944)
    BLOCK_TICKING_QUEUES = auto()
    BIOME_STORAGE = auto()
    BLOBS = value(since=2168)
    CEREAL = auto()
    CIRCUIT_SYSTEM = auto()
    CLIENT = auto()
    COMMANDS = auto()
    DB_STORAGE = value(cpp_name="DBStorage")
    DEBUG = auto()
    DOCUMENTATION = auto()
    ECS_SYSTEMS = value(cpp_name="ECSSystems")
    FMOD = value(cpp_name="FMOD")
    FONTS = auto()
    IM_GUI = auto()
    INPUT = auto()
    JSON_UI = value(cpp_name="JsonUI")
    JSON_UI_CONTROL_FACTORY_JSON = value(cpp_name="JsonUIControlFactoryJson")
    JSON_UI_CONTROL_TREE = value(cpp_name="JsonUIControlTree")
    JSON_UI_CONTROL_TREE_CONTROL_ELEMENT = value(cpp_name="JsonUIControlTreeControlElement")
    JSON_UI_CONTROL_TREE_POPULATE_DATA_BINDING = value(cpp_name="JsonUIControlTreePopulateDataBinding")
    JSON_UI_CONTROL_TREE_POPULATE_FOCUS = value(cpp_name="JsonUIControlTreePopulateFocus")
    JSON_UI_CONTROL_TREE_POPULATE_LAYOUT = value(cpp_name="JsonUIControlTreePopulateLayout")
    JSON_UI_CONTROL_TREE_POPULATE_OTHER = value(cpp_name="JsonUIControlTreePopulateOther")
    JSON_UI_CONTROL_TREE_POPULATE_SPRITE = value(cpp_name="JsonUIControlTreePopulateSprite")
    JSON_UI_CONTROL_TREE_POPULATE_TEXT = value(cpp_name="JsonUIControlTreePopulateText")
    JSON_UI_CONTROL_TREE_POPULATE_TTS = value(cpp_name="JsonUIControlTreePopulateTTS")
    JSON_UI_CONTROL_TREE_VISIBILITY = value(cpp_name="JsonUIControlTreeVisibility")
    JSON_UI_CREATE_UI = value(cpp_name="JsonUICreateUI")
    JSON_UI_DEFS = value(cpp_name="JsonUIDefs")
    JSON_UI_LAYOUT_MANAGER = value(cpp_name="JsonUILayoutManager")
    JSON_UI_LAYOUT_MANAGER_REMOVE_DEPENDENCIES = value(cpp_name="JsonUILayoutManagerRemoveDependencies")
    JSON_UI_LAYOUT_MANAGER_INIT_VARIABLE = value(cpp_name="JsonUILayoutManagerInitVariable")
    LANGUAGES = auto()
    LEVEL = auto()
    LEVEL_STRUCTURES = auto()
    LEVEL_CHUNK = auto()
    LEVEL_CHUNK_GEN = auto()
    LEVEL_CHUNK_GEN_THREAD_LOCAL = auto()
    LIGHT_VOLUME_MANAGER = value(since=944)
    NETWORK = auto()
    MARKETPLACE = value(since=844)
    MATERIAL_DRAGON_COMPILED_DEFINITION = auto()
    MATERIAL_DRAGON_MATERIAL = auto()
    MATERIAL_DRAGON_RESOURCE = auto()
    MATERIAL_DRAGON_UNIFORM_MAP = auto()
    MATERIAL_RENDER_MATERIAL = auto()
    MATERIAL_RENDER_MATERIAL_GROUP = auto()
    MATERIAL_VARIATION_MANAGER = auto()
    MOLANG = auto()
    ORE_UI = value(cpp_name="OreUI")
    PERSONA = value(until=2168)
    with value(since=2168):
        ORE_UI_CLIENT = value(cpp_name="OreUIClient")
        PERSONA_PIECES = auto()
        PERSONA_ANIMATIONS = auto()
        PERSONA_TEXTURES = value(until=2193)
        PERSONA_CHARACTERS = auto()
        PERSONA_SKIN_PACKS = auto()
        PERSONA_REPO = auto()
    PLAYER = auto()
    RENDER_CHUNK = auto()
    RENDER_CHUNK_INDEX_BUFFER = auto()
    RENDER_CHUNK_VERTEX_BUFFER = auto()
    RENDERING = auto()
    with value(since=2168):
        RENDERING_BGFX_INIT = auto()
        RENDERING_BGFX_START_FRAME = auto()
        RENDERING_BLOCK_TESSELLATOR = auto()
        RENDERING_END_FRAME = auto()
        RENDERING_GRAPHICS_TASKS_INIT = auto()
        RENDERING_LIBRARY = auto()
        RENDERING_POLYGON_OPERATOR_POOL = auto()
        RENDERING_PBR_TEXTURE_DATA = value(cpp_name="RenderingPBRTextureData")
    RENDERING_RENDER_REGISTRY = value(since=975)
    RENDERING_LIBRARY = value(until=2168)
    with value(since=2168):
        RENDERING_SETUP = auto()
        RENDERING_VERTICES = auto()
    REQUEST_LOG = value(since=898)
    RESOURCE_PACKS = auto()
    SOUND = auto()
    SUB_CHUNK_BIOME_DATA = auto()
    SUB_CHUNK_BLOCK_DATA = auto()
    SUB_CHUNK_LIGHT_DATA = auto()
    TEXTURES = auto()
    VR = value(until=975)
    WEATHER_RENDERER = auto()
    WORLD_GENERATOR = auto()
    TASKS = auto()
    TEST = auto()
    TEST_LOAD_TEST_TAGS = value(since=2168)
    SCRIPTING = auto()
    SCRIPTING_RUNTIME = auto()
    SCRIPTING_CONTEXT = auto()
    SCRIPTING_CONTEXT_BINDINGS_MC = value(cpp_name="ScriptingContextBindingsMC")
    SCRIPTING_CONTEXT_BINDINGS_GT = value(cpp_name="ScriptingContextBindingsGT")
    SCRIPTING_CONTEXT_RUN = auto()
    with value(since=898):
        DATA_DRIVEN_UI = value(cpp_name="DataDrivenUI")
        DATA_DRIVEN_UI_DEFS = value(cpp_name="DataDrivenUIDefs")
    with value(since=944):
        GAMEFACE = auto()
        GAMEFACE_SYSTEM = auto()
        GAMEFACE_DOM = value(cpp_name="GamefaceDOM")
        GAMEFACE_CSS = value(cpp_name="GamefaceCSS")
        GAMEFACE_DISPLAY = auto()
        GAMEFACE_TEMP_ALLOCATOR = auto()
        GAMEFACE_POOL_ALLOCATOR = auto()
        GAMEFACE_DUMP = auto()
        GAMEFACE_MEDIA = auto()
        GAMEFACE_JSON = value(cpp_name="GamefaceJSON")
        GAMEFACE_SCRIPT_ENGINE = auto()
    with value(since=2168):
        GAMEFACE_SCRIPT = auto()
        GAMEFACE_LAYOUT = auto()
    EXECUTABLE = value(since=2225)
    MEMORY_CATEGORY_COUNT = sentinel()


@type(since=924)
class MemoryCategoryCounter:
    category: MemoryCategory
    current_bytes: uint64


class EntityDiagnosticTimingInfo:
    display_name: str
    entity: str
    time_in_ns: uint64
    percent_of_total: uint8
    with field(since=2193):
        position: Vec3 | None
        dimension: str | None


class SystemDiagnosticTimingInfo:
    display_name: str
    system_index: uint64
    time_in_ns: uint64
    percent_of_total: uint8


@type(since=2168)
class SystemCategory:
    category_name: str
    system_index: uint64


class ScopeDataSummary:
    label: str
    indentation: str
    total_high_cost_ns: uint64
    total_mid_cost_ns: uint64
    total_low_cost_ns: uint64


class EntitySystemDiagnosticSummary:
    entity_timings: list[EntityDiagnosticTimingInfo]
    system_timings: list[SystemDiagnosticTimingInfo]
    system_categories: list[SystemCategory] | None = field(since=2168)


@packet(id=315)
class ServerboundDiagnosticsPacket:
    avg_fps: float
    avg_server_sim_tick_time_ms: float
    avg_client_sim_tick_time_ms: float
    avg_begin_frame_time_ms: float
    avg_input_time_ms: float
    avg_render_time_ms: float
    avg_end_frame_time_ms: float
    avg_remainder_time_percent: float
    avg_unaccounted_time_percent: float
    category_counters: list[MemoryCategoryCounter] = field(since=924)
    entity_system_diagnostics: EntitySystemDiagnosticSummary = field(since=975)
    whisker_data: list[ScopeDataSummary] = field(since=1001)


@packet(id=190, until=944)
class EditorNetworkPacket:
    route_to_manager: bool
    payload: CompoundTag


@packet(id=190, since=944)
class EditorNetworkPacket:
    route_to_manager: bool
    raw_variant_name: str
    raw_variant_data: str


@packet(id=155)
class DebugInfoPacket:
    actor_id: ActorUniqueID
    data: str


@packet(id=164)
class ClientboundDebugRendererPacket:
    class PayloadType(IntEnum, uint8):
        INVALID = 0
        CLEAR_DEBUG_MARKERS = 1
        ADD_DEBUG_MARKER_CUBE = 2

    class DebugMarkerData:
        text: str
        position: Vec3
        color: Color
        duration_ms: uint64

    type: PayloadType = field(type=str)
    debug_marker_data: DebugMarkerData | None
