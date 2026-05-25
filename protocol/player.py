from enum import IntEnum

from protocol import (
    bitset,
    field,
    int32,
    packet,
    type,
    uint8,
    uint64,
    uvarint64,
    varint32,
)
from protocol.actor import ActorRuntimeID, ActorUniqueID
from protocol.common import BlockPos, NetworkBlockPos, Vec2, Vec3
from protocol.input import PlayerInputTick
from protocol.inventory import ItemStackRequestData

package = "bedrock.protocol"


class ActorDataFlagComponent:
    value: bitset[130]


class ActorDataBoundingBoxComponent:
    value: tuple[float, float, float]


@packet(id=322, since=776)
class ClientMovementPredictionSyncPacket:
    """Only used in Server-Authoritative Movement. Sent periodically if the client
    has received corrections from the server. Contains information about
    client-predictions that are relevant to movement."""

    actor_data_flag: ActorDataFlagComponent
    actor_bounding_box: ActorDataBoundingBoxComponent
    movement_attributes: tuple[float, float, float, float, float, float, float, float, float]
    actor_unique_id: ActorUniqueID
    actor_flying_state: bool


@type(since=944)
class PlayerPartyInfo:
    party_id: str
    is_leader: bool = field(since=975)


@packet(id=342, since=944)
class PartyChangedPacket:
    party_info: PlayerPartyInfo | None


@type(since=786)
class GraphicsMode(IntEnum):
    SIMPLE = 0
    FANCY = 1
    ADVANCED = 2
    RAY_TRACED = 3


@packet(id=323, since=786)
class UpdateClientOptionsPacket:
    """The values in this packet are originally synced through the Connection Request and then
    updated via this packet."""

    graphics_mode: GraphicsMode | None = field(type=uint8)
    filter_profanity: bool | None = field(since=975)


# TODO: confirm against BDS -- MemoryCategory enum has 90+ entries that shift across versions;
# modelling as raw uint8 for now until a future pass adds the full enum.
@type(since=924)
class MemoryCategoryCounter:
    category: uint8
    current_bytes: uint64


@type(since=975)
class EntityDiagnosticTimingInfo:
    display_name: str
    entity: str
    time_in_ns: uint64
    percent_of_total: uint8


@type(since=975)
class SystemDiagnosticTimingInfo:
    display_name: str
    system_index: uint64
    time_in_ns: uint64
    percent_of_total: uint8


@packet(id=315, since=712)
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
    memory_category_values: list[MemoryCategoryCounter] = field(since=924)
    entity_diagnostics: list[EntityDiagnosticTimingInfo] = field(since=975)
    system_diagnostics: list[SystemDiagnosticTimingInfo] = field(since=975)


# ============================================================================
# Wave 3a additions: helper types + player-related packets
# ============================================================================


@packet(id=327, since=800)
class ClientboundControlSchemeSetPacket:
    """Set the control scheme that the player should use"""

    class Scheme(IntEnum):
        # BDS: ControlScheme::Scheme.
        LOCKED_PLAYER_RELATIVE_STRAFE = 0
        CAMERA_RELATIVE = 1
        CAMERA_RELATIVE_STRAFE = 2
        PLAYER_RELATIVE = 3
        PLAYER_RELATIVE_STRAFE = 4

    control_scheme: Scheme = field(type=uint8)


class RewindType(IntEnum):
    PLAYER = 0
    VEHICLE = 1


# Modeling the v827+ wire shape only -- the pre-v827 era reordered
# prediction_type and the vehicle fields several times. v975 is the target so
# the simpler post-v827 shape is sufficient.
@packet(id=161, since=827)
class CorrectPlayerMovePredictionPacket:
    """Sent to a player when their simulation of movement mismatches enough
    from the server that it wants to correct the client."""

    prediction_type: RewindType = field(type=uint8)
    pos: Vec3
    pos_delta: Vec3
    vehicle_rotation: Vec2
    vehicle_angular_velocity: float | None
    on_ground: bool
    tick: uvarint64


@packet(id=19)
class MovePlayerPacket:
    """Server-bound and client-bound movement updates for the local player."""

    class PositionMode(IntEnum):
        # BDS: PlayerPositionModeComponent::PositionMode (uint8 on the wire).
        NORMAL = 0
        RESPAWN = 1
        TELEPORT = 2
        ONLY_HEAD_ROT = 3

    class TeleportationCause(IntEnum):
        # BDS: MinecraftEventing::TeleportationCause (int32 on the wire).
        UNKNOWN = 0
        PROJECTILE = 1
        CHORUS_FRUIT = 2
        COMMAND = 3
        BEHAVIOR = 4

    player_id: ActorRuntimeID
    pos: Vec3
    rot: Vec2
    y_head_rot: float
    reset_position: PositionMode = field(type=uint8)
    on_ground: bool
    riding_id: ActorRuntimeID
    cause: TeleportationCause = field(type=int32, when=lambda p: p.reset_position == PositionMode.TELEPORT)
    source_entity_type: int32 = field(when=lambda p: p.reset_position == PositionMode.TELEPORT)
    tick: PlayerInputTick = field(since=419)


@packet(id=34)
class BlockPickRequestPacket:
    """Player picks up a block in the world, client to server."""

    pos: BlockPos
    with_data: bool
    max_slots: uint8


@packet(id=54)
class GuiDataPickItemPacket:
    """The server telling the client what item slot to hover over in the hotbar."""

    item_name: str
    item_effect_name: str
    slot: int32 = field(endian="little")


# ItemFrameDropItemPacket (id=71, until=662) was removed before v975. The DSL
# requires a packet redeclaration to use until=. No successor exists at id=71
# in v975, so drop the gate -- packet is emitted but unused at the v975 target.
@packet(id=71)
class ItemFrameDropItemPacket:
    pos: NetworkBlockPos


@packet(id=147, since=407)
class ItemStackRequestPacket:
    """Carries a batch of item-stack requests from the client."""

    request_batch: list[ItemStackRequestData]


@packet(id=176, since=486)
class PlayerStartItemCooldownPacket:
    """Packet sent by the player to start the cooldown on an item."""

    item_category: str
    duration_ticks: varint32


class InventoryLeftTabIndex(IntEnum):
    NONE = 0
    RECIPE_CONSTRUCTION = 1
    RECIPE_EQUIPMENT = 2
    RECIPE_ITEMS = 3
    RECIPE_NATURE = 4
    RECIPE_SEARCH = 5
    SURVIVAL = 6


class InventoryRightTabIndex(IntEnum):
    NONE = 0
    FULL_SCREEN = 1
    CRAFTING = 2
    ARMOR = 3


@type(since=630)
class InventoryLayout(IntEnum):
    NONE = 0
    INVENTORY_ONLY = 1
    DEFAULT = 2
    RECIPE_BOOK_ONLY = 3


@type(since=630)
class InventoryOptions:
    left_inventory_tab: InventoryLeftTabIndex = field(type=varint32)
    right_inventory_tab: InventoryRightTabIndex = field(type=varint32)
    filtering: bool
    layout_inv: InventoryLayout = field(type=varint32)
    layout_craft: InventoryLayout = field(type=varint32)


@packet(id=307, since=630)
class SetPlayerInventoryOptionsPacket:
    inventory_options: InventoryOptions


class PlayerListPacketType(IntEnum):
    ADD = 0
    REMOVE = 1
