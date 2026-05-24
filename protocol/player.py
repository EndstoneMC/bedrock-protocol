from enum import IntEnum, auto

from protocol import bitset, field, packet, type, uint8, uint64, uvarint32, uvarint64, value, varint32
from protocol.actor import ActorUniqueID
from protocol.common import BlockPos, Vec2, Vec3
from protocol.inventory import (
    ItemStackRequestData,
    PackedItemUseLegacyInventoryTransaction,
)

package = "bedrock.protocol"

type PlayerInputTick = uvarint64


class InputMode(IntEnum):
    UNDEFINED = 0
    MOUSE = 1
    TOUCH = 2
    GAME_PAD = 3
    MOTION_CONTROLLER = value(4, deprecated=859)
    COUNT = auto()


class ClientPlayMode(IntEnum):
    NORMAL = 0
    TEASER = 1
    SCREEN = 2
    VIEWER = value(3, deprecated=859)
    REALITY = value(4, deprecated=859)
    PLACEMENT = value(5, deprecated=859)
    LIVING_ROOM = value(6, deprecated=859)
    EXIT_LEVEL = 7
    EXIT_LEVEL_LIVING_ROOM = value(8, deprecated=859)
    NUM_MODES = auto()


@type(since=527)
class NewInteractionModel(IntEnum):
    TOUCH = 0
    CROSSHAIR = 1
    CLASSIC = 2
    COUNT = auto()


class PlayerActionType(IntEnum):
    START_DESTROY_BLOCK = 0
    ABORT_DESTROY_BLOCK = 1
    STOP_DESTROY_BLOCK = 2
    GET_UPDATED_BLOCK = 3
    DROP_ITEM = 4
    START_SLEEPING = 5
    STOP_SLEEPING = 6
    RESPAWN = 7
    START_JUMP = 8
    START_SPRINTING = 9
    STOP_SPRINTING = 10
    START_SNEAKING = 11
    STOP_SNEAKING = 12
    CREATIVE_DESTROY_BLOCK = 13
    CHANGE_DIMENSION_ACK = 14
    START_GLIDING = 15
    STOP_GLIDING = 16
    DENY_DESTROY_BLOCK = 17
    CRACK_BLOCK = 18
    CHANGE_SKIN = 19
    UPDATED_ENCHANTING_SEED = 20
    START_SWIMMING = 21
    STOP_SWIMMING = 22
    START_SPIN_ATTACK = 23
    STOP_SPIN_ATTACK = 24
    INTERACT_WITH_BLOCK = 25
    PREDICT_DESTROY_BLOCK = 26
    CONTINUE_DESTROY_BLOCK = 27
    START_ITEM_USE_ON = 28
    STOP_ITEM_USE_ON = 29
    HANDLED_TELEPORT = 30
    MISSED_SWING = 31
    START_CRAWLING = 32
    STOP_CRAWLING = 33
    START_FLYING = 34
    STOP_FLYING = 35
    CLIENT_ACK_SERVER_DATA = 36
    START_USING_ITEM = 37
    COUNT = auto()


class PlayerBlockActionData:
    player_action_type: PlayerActionType = field(type=varint32)
    with field(
        when=lambda p: (
            p.player_action_type == PlayerActionType.START_DESTROY_BLOCK
            or p.player_action_type == PlayerActionType.ABORT_DESTROY_BLOCK
            or p.player_action_type == PlayerActionType.CRACK_BLOCK
            or p.player_action_type == PlayerActionType.PREDICT_DESTROY_BLOCK
            or p.player_action_type == PlayerActionType.CONTINUE_DESTROY_BLOCK
        )
    ):
        pos: BlockPos
        facing: varint32


class PlayerBlockActions:
    actions: list[PlayerBlockActionData] = field(prefix=varint32)


@packet(id=144, since=388)
class PlayerAuthInputPacket:
    class InputData(IntEnum):
        ASCEND = 0
        DESCEND = 1
        NORTH_JUMP = value(2, deprecated=685)
        JUMP_DOWN = 3
        SPRINT_DOWN = 4
        CHANGE_HEIGHT = 5
        JUMPING = 6
        AUTO_JUMPING_IN_WATER = 7
        SNEAKING = 8
        SNEAK_DOWN = 9
        UP = 10
        DOWN = 11
        LEFT = 12
        RIGHT = 13
        UP_LEFT = 14
        UP_RIGHT = 15
        WANT_UP = 16
        WANT_DOWN = 17
        WANT_DOWN_SLOW = 18
        WANT_UP_SLOW = 19
        SPRINTING = 20
        ASCEND_BLOCK = 21
        DESCEND_BLOCK = 22
        SNEAK_TOGGLE_DOWN = 23
        PERSIST_SNEAK = 24
        START_SPRINTING = 25
        STOP_SPRINTING = 26
        START_SNEAKING = 27
        STOP_SNEAKING = 28
        START_SWIMMING = 29
        STOP_SWIMMING = 30
        START_JUMPING = 31
        START_GLIDING = 32
        STOP_GLIDING = 33
        PERFORM_ITEM_INTERACTION = 34
        PERFORM_BLOCK_ACTIONS = 35
        PERFORM_ITEM_STACK_REQUEST = 36
        HANDLED_TELEPORT = value(37, since=567)
        EMOTING = value(38, since=575)
        MISSED_SWING = value(39, since=594)
        START_CRAWLING = value(40, since=594)
        STOP_CRAWLING = value(41, since=594)
        START_FLYING = value(42, since=618)
        STOP_FLYING = value(43, since=618)
        CLIENT_ACK_SERVER_DATA = value(44, since=622)
        IS_IN_CLIENT_PREDICTED_VEHICLE = value(45, since=649)
        PADDLING_LEFT = value(46, since=662)
        PADDLING_RIGHT = value(47, since=662)
        BLOCK_BREAKING_DELAY_ENABLED = value(48, since=685)
        HORIZONTAL_COLLISION = value(49, since=729)
        VERTICAL_COLLISION = value(50, since=729)
        DOWN_LEFT = value(51, since=729)
        DOWN_RIGHT = value(52, since=729)
        START_USING_ITEM = value(53, since=748)
        IS_CAMERA_RELATIVE_MOVEMENT_ENABLED = value(54, since=748, deprecated=859)
        IS_ROT_CONTROLLED_BY_MOVE_DIRECTION = value(55, since=748, deprecated=859)
        START_SPIN_ATTACK = value(56, since=748)
        STOP_SPIN_ATTACK = value(57, since=748)
        IS_HOTBAR_ONLY_TOUCH = value(58, since=766)
        JUMP_RELEASED_RAW = value(59, since=766)
        JUMP_PRESSED_RAW = value(60, since=766)
        JUMP_CURRENT_RAW = value(61, since=766)
        SNEAK_RELEASED_RAW = value(62, since=766)
        SNEAK_PRESSED_RAW = value(63, since=766)
        SNEAK_CURRENT_RAW = value(64, since=766)
        INPUT_NUM = auto()

    rot: Vec2
    pos: Vec3
    move: Vec2
    y_head_rot: float
    input_data: bitset[InputData.INPUT_NUM]
    input_mode: InputMode = field(type=uvarint32)
    play_mode: ClientPlayMode = field(type=uvarint32)
    new_interaction_model: NewInteractionModel = field(type=uvarint32, since=527)
    vr_gaze_direction: Vec3 = field(  # TODO: confirm against BDS
        when=lambda p: p.play_mode == ClientPlayMode.REALITY,
        until=748,
    )
    interact_rotation: Vec2 = field(since=748)
    client_tick: PlayerInputTick = field(since=419)
    pos_delta: Vec3 = field(since=419)
    item_use_transaction: PackedItemUseLegacyInventoryTransaction = field(
        when=lambda p: p.input_data.test(InputData.PERFORM_ITEM_INTERACTION),
    )
    item_stack_request: ItemStackRequestData = field(
        when=lambda p: p.input_data.test(InputData.PERFORM_ITEM_STACK_REQUEST),
    )
    player_block_actions: PlayerBlockActions = field(
        when=lambda p: p.input_data.test(InputData.PERFORM_BLOCK_ACTIONS),
    )
    with field(
        when=lambda p: p.input_data.test(InputData.IS_IN_CLIENT_PREDICTED_VEHICLE)
    ):
        vehicle_rot: Vec2 = field(since=662)
        client_predicted_vehicle: ActorUniqueID = field(since=649)
    analog_move_vector: Vec2 = field(since=575)
    camera_orientation: Vec3 = field(since=748)
    raw_move_vector: Vec2 = field(since=766)


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
    movement_attributes: tuple[
        float, float, float, float, float, float, float, float, float
    ]
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
