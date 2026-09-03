"""What the client reports for diagnosis: profile/ Whisker scopes, memory categories,
frame and system timings, plus debug/ markers and the editor channel."""

from enum import Enum, IntEnum

from protocol import auto, field, packet, type, uint8, uint64, value
from protocol.actor import ActorUniqueID
from protocol.common import Color, Vec3

package = "bedrock.protocol"


@type(until=2168)
class MemoryCategory(IntEnum, uint8):
    UNKNOWN = 0
    INVALID_SIZE_UNKNOWN = 1
    ACTOR = 2
    ACTOR_ANIMATION = 3
    ACTOR_RENDERING = 4
    BLOCK_TICKING_QUEUES = 5
    BIOME_STORAGE = 6
    CEREAL = 7
    CIRCUIT_SYSTEM = 8
    CLIENT = 9
    COMMANDS = 10
    DB_STORAGE = 11
    DEBUG = 12
    DOCUMENTATION = 13
    ECS_SYSTEMS = 14
    FMOD = 15
    FONTS = 16
    IM_GUI = 17
    INPUT = 18
    JSON_UI = 19
    JSON_UI_CONTROL_FACTORY_JSON = 20
    JSON_UI_CONTROL_TREE = 21
    JSON_UI_CONTROL_TREE_CONTROL_ELEMENT = 22
    JSON_UI_CONTROL_TREE_POPULATE_DATA_BINDING = 23
    JSON_UI_CONTROL_TREE_POPULATE_FOCUS = 24
    JSON_UI_CONTROL_TREE_POPULATE_LAYOUT = 25
    JSON_UI_CONTROL_TREE_POPULATE_OTHER = 26
    JSON_UI_CONTROL_TREE_POPULATE_SPRITE = 27
    JSON_UI_CONTROL_TREE_POPULATE_TEXT = 28
    JSON_UI_CONTROL_TREE_POPULATE_TTS = 29
    JSON_UI_CONTROL_TREE_VISIBILITY = 30
    JSON_UI_CREATE_UI = 31
    JSON_UI_DEFS = 32
    JSON_UI_LAYOUT_MANAGER = 33
    JSON_UI_LAYOUT_MANAGER_REMOVE_DEPENDENCIES = 34
    JSON_UI_LAYOUT_MANAGER_INIT_VARIABLE = 35
    LANGUAGES = 36
    LEVEL = 37
    LEVEL_STRUCTURES = 38
    LEVEL_CHUNK = 39
    LEVEL_CHUNK_GEN = 40
    LEVEL_CHUNK_GEN_THREAD_LOCAL = 41
    LIGHT_VOLUME_MANAGER = 42
    NETWORK = 43
    MARKETPLACE = 44
    MATERIAL_DRAGON_COMPILED_DEFINITION = 45
    MATERIAL_DRAGON_MATERIAL = 46
    MATERIAL_DRAGON_RESOURCE = 47
    MATERIAL_DRAGON_UNIFORM_MAP = 48
    MATERIAL_RENDER_MATERIAL = 49
    MATERIAL_RENDER_MATERIAL_GROUP = 50
    MATERIAL_VARIATION_MANAGER = 51
    MOLANG = 52
    ORE_UI = 53
    PERSONA = 54
    PLAYER = 55
    RENDER_CHUNK = 56
    RENDER_CHUNK_INDEX_BUFFER = 57
    RENDER_CHUNK_VERTEX_BUFFER = 58
    RENDERING = 59
    RENDERING_RENDER_REGISTRY = 60
    RENDERING_LIBRARY = 61
    REQUEST_LOG = 62
    RESOURCE_PACKS = 63
    SOUND = 64
    SUB_CHUNK_BIOME_DATA = 65
    SUB_CHUNK_BLOCK_DATA = 66
    SUB_CHUNK_LIGHT_DATA = 67
    TEXTURES = 68
    WEATHER_RENDERER = 69
    WORLD_GENERATOR = 70
    TASKS = 71
    TEST = 72
    SCRIPTING = 73
    SCRIPTING_RUNTIME = 74
    SCRIPTING_CONTEXT = 75
    SCRIPTING_CONTEXT_BINDINGS_MC = 76
    SCRIPTING_CONTEXT_BINDINGS_GT = 77
    SCRIPTING_CONTEXT_RUN = 78
    DATA_DRIVEN_UI = 79
    DATA_DRIVEN_UI_DEFS = 80
    GAMEFACE = 81
    GAMEFACE_SYSTEM = 82
    GAMEFACE_DOM = 83
    GAMEFACE_CSS = 84
    GAMEFACE_DISPLAY = 85
    GAMEFACE_TEMP_ALLOCATOR = 86
    GAMEFACE_POOL_ALLOCATOR = 87
    GAMEFACE_DUMP = 88
    GAMEFACE_MEDIA = 89
    GAMEFACE_JSON = 90
    GAMEFACE_SCRIPT_ENGINE = 91
    COUNT = auto()


@type(since=2168)
class MemoryCategory(IntEnum, uint8):
    UNKNOWN = 0
    INVALID_SIZE_UNKNOWN = 1
    ACTOR = 2
    ACTOR_ANIMATION = 3
    ACTOR_RENDERING = 4
    BLOCK_TICKING_QUEUES = 5
    BIOME_STORAGE = 6
    BLOBS = 7
    CEREAL = 8
    CIRCUIT_SYSTEM = 9
    CLIENT = 10
    COMMANDS = 11
    DB_STORAGE = 12
    DEBUG = 13
    DOCUMENTATION = 14
    ECS_SYSTEMS = 15
    FMOD = 16
    FONTS = 17
    IM_GUI = 18
    INPUT = 19
    JSON_UI = 20
    JSON_UI_CONTROL_FACTORY_JSON = 21
    JSON_UI_CONTROL_TREE = 22
    JSON_UI_CONTROL_TREE_CONTROL_ELEMENT = 23
    JSON_UI_CONTROL_TREE_POPULATE_DATA_BINDING = 24
    JSON_UI_CONTROL_TREE_POPULATE_FOCUS = 25
    JSON_UI_CONTROL_TREE_POPULATE_LAYOUT = 26
    JSON_UI_CONTROL_TREE_POPULATE_OTHER = 27
    JSON_UI_CONTROL_TREE_POPULATE_SPRITE = 28
    JSON_UI_CONTROL_TREE_POPULATE_TEXT = 29
    JSON_UI_CONTROL_TREE_POPULATE_TTS = 30
    JSON_UI_CONTROL_TREE_VISIBILITY = 31
    JSON_UI_CREATE_UI = 32
    JSON_UI_DEFS = 33
    JSON_UI_LAYOUT_MANAGER = 34
    JSON_UI_LAYOUT_MANAGER_REMOVE_DEPENDENCIES = 35
    JSON_UI_LAYOUT_MANAGER_INIT_VARIABLE = 36
    LANGUAGES = 37
    LEVEL = 38
    LEVEL_STRUCTURES = 39
    LEVEL_CHUNK = 40
    LEVEL_CHUNK_GEN = 41
    LEVEL_CHUNK_GEN_THREAD_LOCAL = 42
    LIGHT_VOLUME_MANAGER = 43
    NETWORK = 44
    MARKETPLACE = 45
    MATERIAL_DRAGON_COMPILED_DEFINITION = 46
    MATERIAL_DRAGON_MATERIAL = 47
    MATERIAL_DRAGON_RESOURCE = 48
    MATERIAL_DRAGON_UNIFORM_MAP = 49
    MATERIAL_RENDER_MATERIAL = 50
    MATERIAL_RENDER_MATERIAL_GROUP = 51
    MATERIAL_VARIATION_MANAGER = 52
    MOLANG = 53
    ORE_UI = 54
    ORE_UI_CLIENT = 55
    PERSONA_PIECES = 56
    PERSONA_ANIMATIONS = 57
    PERSONA_TEXTURES = value(58, until=2192)
    PERSONA_CHARACTERS = auto()
    PERSONA_SKIN_PACKS = auto()
    PERSONA_REPO = auto()
    PLAYER = auto()
    RENDER_CHUNK = auto()
    RENDER_CHUNK_INDEX_BUFFER = auto()
    RENDER_CHUNK_VERTEX_BUFFER = auto()
    RENDERING = auto()
    RENDERING_BGFX_INIT = auto()
    RENDERING_BGFX_START_FRAME = auto()
    RENDERING_BLOCK_TESSELLATOR = auto()
    RENDERING_END_FRAME = auto()
    RENDERING_GRAPHICS_TASKS_INIT = auto()
    RENDERING_LIBRARY = auto()
    RENDERING_POLYGON_OPERATOR_POOL = auto()
    RENDERING_PBR_TEXTURE_DATA = auto()
    RENDERING_RENDER_REGISTRY = auto()
    RENDERING_SETUP = auto()
    RENDERING_VERTICES = auto()
    REQUEST_LOG = auto()
    RESOURCE_PACKS = auto()
    SOUND = auto()
    SUB_CHUNK_BIOME_DATA = auto()
    SUB_CHUNK_BLOCK_DATA = auto()
    SUB_CHUNK_LIGHT_DATA = auto()
    TEXTURES = auto()
    WEATHER_RENDERER = auto()
    WORLD_GENERATOR = auto()
    TASKS = auto()
    TEST = auto()
    TEST_LOAD_TEST_TAGS = auto()
    SCRIPTING = auto()
    SCRIPTING_RUNTIME = auto()
    SCRIPTING_CONTEXT = auto()
    SCRIPTING_CONTEXT_BINDINGS_MC = auto()
    SCRIPTING_CONTEXT_BINDINGS_GT = auto()
    SCRIPTING_CONTEXT_RUN = auto()
    DATA_DRIVEN_UI = auto()
    DATA_DRIVEN_UI_DEFS = auto()
    GAMEFACE = auto()
    GAMEFACE_SYSTEM = auto()
    GAMEFACE_DOM = auto()
    GAMEFACE_CSS = auto()
    GAMEFACE_DISPLAY = auto()
    GAMEFACE_TEMP_ALLOCATOR = auto()
    GAMEFACE_POOL_ALLOCATOR = auto()
    GAMEFACE_DUMP = auto()
    GAMEFACE_MEDIA = auto()
    GAMEFACE_JSON = auto()
    GAMEFACE_SCRIPT_ENGINE = auto()
    GAMEFACE_SCRIPT = auto()
    GAMEFACE_LAYOUT = auto()
    COUNT = auto()


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
    category_counters: list[MemoryCategoryCounter]
    entity_timings: list[EntityDiagnosticTimingInfo]
    system_timings: list[SystemDiagnosticTimingInfo]
    system_categories: list[SystemCategory] | None = field(since=2168)
    whisker_data: list[ScopeDataSummary] = field(since=1001)


@packet(id=190, since=2168)
class EditorNetworkPacket:
    route_to_manager: bool
    raw_variant_name: str
    raw_variant_data: str


@packet(id=155, since=2168)
class DebugInfoPacket:
    actor_id: ActorUniqueID
    data: str


@packet(id=164, since=2168)
class ClientboundDebugRendererPacket:
    class PayloadType(Enum, uint8):
        INVALID = 0
        CLEAR_DEBUG_MARKERS = 1, "ClearDebugMarkers"
        ADD_DEBUG_MARKER_CUBE = 2, "AddDebugMarkerCube"

    class DebugMarkerData:
        text: str
        position: Vec3
        color: Color
        duration_ms: uint64

    type: PayloadType = field(type=str)
    debug_marker_data: DebugMarkerData | None
