"""What the client reports for diagnosis: profile/ Whisker scopes, memory categories,
frame and system timings, plus debug/ markers and the editor channel."""

from enum import Enum, IntEnum

from protocol import auto, field, packet, type, uint8, uint64, value
from protocol.actor import ActorUniqueID
from protocol.common import Color, Vec3
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


class MemoryCategory(IntEnum, uint8):
    UNKNOWN = 0
    INVALID_SIZE_UNKNOWN = auto()
    ACTOR = auto()
    ACTOR_ANIMATION = auto()
    ACTOR_RENDERING = auto()
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
    MARKETPLACE = auto()
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
    ORE_UI_CLIENT = value(cpp_name="OreUIClient", since=2168)
    PERSONA_PIECES = value(since=2168)
    PERSONA_ANIMATIONS = value(since=2168)
    PERSONA_TEXTURES = value(until=2192, since=2168)
    PERSONA_CHARACTERS = value(since=2168)
    PERSONA_SKIN_PACKS = value(since=2168)
    PERSONA_REPO = value(since=2168)
    PLAYER = auto()
    RENDER_CHUNK = auto()
    RENDER_CHUNK_INDEX_BUFFER = auto()
    RENDER_CHUNK_VERTEX_BUFFER = auto()
    RENDERING = auto()
    RENDERING_BGFX_INIT = value(since=2168)
    RENDERING_BGFX_START_FRAME = value(since=2168)
    RENDERING_BLOCK_TESSELLATOR = value(since=2168)
    RENDERING_END_FRAME = value(since=2168)
    RENDERING_GRAPHICS_TASKS_INIT = value(since=2168)
    RENDERING_LIBRARY = value(since=2168)
    RENDERING_POLYGON_OPERATOR_POOL = value(since=2168)
    RENDERING_PBR_TEXTURE_DATA = value(cpp_name="RenderingPBRTextureData", since=2168)
    RENDERING_RENDER_REGISTRY = value(since=975)
    RENDERING_LIBRARY = value(until=2168)
    RENDERING_SETUP = value(since=2168)
    RENDERING_VERTICES = value(since=2168)
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
    DATA_DRIVEN_UI = value(cpp_name="DataDrivenUI", since=898)
    DATA_DRIVEN_UI_DEFS = value(cpp_name="DataDrivenUIDefs", since=898)
    GAMEFACE = value(since=944)
    GAMEFACE_SYSTEM = value(since=944)
    GAMEFACE_DOM = value(cpp_name="GamefaceDOM", since=944)
    GAMEFACE_CSS = value(cpp_name="GamefaceCSS", since=944)
    GAMEFACE_DISPLAY = value(since=944)
    GAMEFACE_TEMP_ALLOCATOR = value(since=944)
    GAMEFACE_POOL_ALLOCATOR = value(since=944)
    GAMEFACE_DUMP = value(since=944)
    GAMEFACE_MEDIA = value(since=944)
    GAMEFACE_JSON = value(cpp_name="GamefaceJSON", since=944)
    GAMEFACE_SCRIPT_ENGINE = value(since=944)
    GAMEFACE_SCRIPT = value(since=2168)
    GAMEFACE_LAYOUT = value(since=2168)
    COUNT = auto()
@type(since=924)
class MemoryCategoryCounter:
    category: MemoryCategory
    current_bytes: uint64


class EntityDiagnosticTimingInfo:
    display_name: str
    entity: str
    time_in_ns: uint64
    percent_of_total: uint8
    position: Vec3 | None = field(since=2192)
    dimension: str | None = field(since=2192)


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
    entity_timings: list[EntityDiagnosticTimingInfo] = field(since=975)
    system_timings: list[SystemDiagnosticTimingInfo] = field(since=975)
    system_categories: list[SystemCategory] | None = field(since=2168)
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
    class PayloadType(Enum, uint8):
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
