import enum

from protocol import field, packet, uint8, uint64

package = "bedrock.protocol"


# TODO: enumerator stub -- BDS declares 92 members (Unknown=0 ..
# Gameface_ScriptEngine=91, MemoryCategory_count=92); only UNKNOWN is named so far.
class MemoryCategory(enum.IntEnum, uint8):
    UNKNOWN = 0


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
