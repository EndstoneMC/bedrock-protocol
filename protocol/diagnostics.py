import enum

from protocol import field, packet, uint8, uint64

package = "bedrock.protocol"


class MemoryCategory(enum.IntEnum, uint8):
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
    COUNT = enum.auto()


class MemoryCategoryCounter:
    category: MemoryCategory
    current_bytes: uint64


class EntityDiagnosticTimingInfo:
    display_name: str
    entity: str
    time_in_ns: uint64
    percent_of_total: uint8


class SystemDiagnosticTimingInfo:
    display_name: str
    system_index: uint64
    time_in_ns: uint64
    percent_of_total: uint8


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
    memory_category_values: list[MemoryCategoryCounter]
    entity_diagnostics: list[EntityDiagnosticTimingInfo]
    system_diagnostics: list[SystemDiagnosticTimingInfo]
    whisker_scopes: list[ScopeDataSummary] = field(since=1001)
