from enum import IntEnum, auto
from typing import Literal

from protocol import bitset, field, packet, type, uint32, uvarint32, value, varint32
from protocol.actor import ActorRuntimeID, ActorUniqueID, PlayerInputTick
from protocol.common import BlockPos, Vec2, Vec3
from protocol.inventory import (
    ItemStackLegacyRequestId,
    ItemUseInventoryTransaction,
    LegacySetSlot,
)
from protocol.item_stack import ItemStackRequestCereal, ItemStackRequestData

package = "bedrock.protocol"


class InputMode(IntEnum, uint32):
    UNDEFINED = 0
    MOUSE = 1
    TOUCH = 2
    GAME_PAD = 3
    MOTION_CONTROLLER_DEPRECATED = 4
    COUNT = auto()


class ClientPlayMode(IntEnum, uint32):
    NORMAL = 0
    TEASER = 1
    SCREEN = 2
    VIEWER_DEPRECATED = 3
    REALITY_DEPRECATED = 4
    PLACEMENT_DEPRECATED = 5
    LIVING_ROOM_DEPRECATED = 6
    EXIT_LEVEL = 7
    EXIT_LEVEL_LIVING_ROOM_DEPRECATED = 8
    NUM_MODES = auto()


class NewInteractionModel(IntEnum, int):
    TOUCH = 0
    CROSSHAIR = 1
    CLASSIC = 2
    COUNT = auto()


class PlayerActionType(IntEnum, int):
    UNKNOWN = -1
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
    DEPRECATED_UPDATED_ENCHANTING_SEED = 20
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
    DEPRECATED_CLIENT_ACK_SERVER_DATA = 36
    START_USING_ITEM = 37
    INTERNAL_UPDATE = value(38, since=2168)
    COUNT = auto()


@type(until=2168)
class PlayerBlockActionData:
    player_action_type: PlayerActionType

    with field(
        when=lambda a: (
            a.player_action_type
            in {
                PlayerActionType.START_DESTROY_BLOCK,
                PlayerActionType.ABORT_DESTROY_BLOCK,
                PlayerActionType.CRACK_BLOCK,
                PlayerActionType.PREDICT_DESTROY_BLOCK,
                PlayerActionType.CONTINUE_DESTROY_BLOCK,
            }
        )
    ):
        pos: BlockPos
        facing: varint32


@type(since=2168)
class PlayerBlockActionData:
    player_action_type: PlayerActionType
    pos: BlockPos
    facing: varint32


# TODO: confirm against BDS -- the slot gate is gophertunnel's, which reads the id as the
# ItemStackNetIdVariant projection: only a negative-even id is a legacy request. Packet 30's
# pre-cereal body gates the same slots on `!= 0`, and the two part company below -1.
@type(until=2168)
class PackedItemUseLegacyInventoryTransaction:
    id: varint32
    slots: list[LegacySetSlot] = field(when=lambda t: t.id < -1 and t.id & 1 == 0)
    transaction: ItemUseInventoryTransaction = field(cereal=False)


@type(since=2168)
class PackedItemUseLegacyInventoryTransaction:
    id: ItemStackLegacyRequestId
    slots: list[LegacySetSlot] | None
    _true_1: Literal[True]
    transaction: ItemUseInventoryTransaction


@packet(id=144, until=2168)
class PlayerAuthInputPacket:
    class InputData(IntEnum, uint32):
        ASCEND = 0
        DESCEND = 1
        NORTH_JUMP_DEPRECATED = 2
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
        HANDLED_TELEPORT = 37
        EMOTING = 38
        MISSED_SWING = 39
        START_CRAWLING = 40
        STOP_CRAWLING = 41
        START_FLYING = 42
        STOP_FLYING = 43
        CLIENT_ACK_SERVER_DATA = 44
        IS_IN_CLIENT_PREDICTED_VEHICLE = 45
        PADDLING_LEFT = 46
        PADDLING_RIGHT = 47
        BLOCK_BREAKING_DELAY_ENABLED = 48
        HORIZONTAL_COLLISION = 49
        VERTICAL_COLLISION = 50
        DOWN_LEFT = 51
        DOWN_RIGHT = 52
        START_USING_ITEM = 53
        IS_CAMERA_RELATIVE_MOVEMENT_ENABLED_DEPRECATED = 54
        IS_ROT_CONTROLLED_BY_MOVE_DIRECTION_DEPRECATED = 55
        START_SPIN_ATTACK = 56
        STOP_SPIN_ATTACK = 57
        IS_HOTBAR_ONLY_TOUCH = 58
        JUMP_RELEASED_RAW = 59
        JUMP_PRESSED_RAW = 60
        JUMP_CURRENT_RAW = 61
        SNEAK_RELEASED_RAW = 62
        SNEAK_PRESSED_RAW = 63
        SNEAK_CURRENT_RAW = 64
        INPUT_NUM = auto()

    rot: Vec2
    pos: Vec3
    move: Vec2
    y_head_rot: float
    input_data: bitset[InputData.INPUT_NUM]
    input_mode: InputMode
    play_mode: ClientPlayMode
    new_interaction_model: NewInteractionModel = field(type=uvarint32)
    interact_rotation: Vec2
    client_tick: PlayerInputTick
    pos_delta: Vec3
    item_use_transaction: PackedItemUseLegacyInventoryTransaction = field(
        when=lambda p: p.input_data.test(InputData.PERFORM_ITEM_INTERACTION)
    )
    item_stack_request: ItemStackRequestData = field(
        when=lambda p: p.input_data.test(InputData.PERFORM_ITEM_STACK_REQUEST)
    )
    player_block_actions: list[PlayerBlockActionData] = field(
        when=lambda p: p.input_data.test(InputData.PERFORM_BLOCK_ACTIONS), prefix=varint32
    )

    with field(when=lambda p: p.input_data.test(InputData.IS_IN_CLIENT_PREDICTED_VEHICLE)):
        vehicle_rot: Vec2
        client_predicted_vehicle: ActorUniqueID

    analog_move_vector: Vec2
    camera_orientation: Vec3
    raw_move_vector: Vec2


@packet(id=144, since=2168)
class PlayerAuthInputPacket:
    class InputData(IntEnum, uint32):
        ASCEND = 0
        DESCEND = 1
        NORTH_JUMP_DEPRECATED = 2
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
        HANDLED_TELEPORT = 37
        EMOTING = 38
        MISSED_SWING = 39
        START_CRAWLING = 40
        STOP_CRAWLING = 41
        START_FLYING = 42
        STOP_FLYING = 43
        CLIENT_ACK_SERVER_DATA = 44
        IS_IN_CLIENT_PREDICTED_VEHICLE = 45
        PADDLING_LEFT = 46
        PADDLING_RIGHT = 47
        BLOCK_BREAKING_DELAY_ENABLED = 48
        HORIZONTAL_COLLISION = 49
        VERTICAL_COLLISION = 50
        DOWN_LEFT = 51
        DOWN_RIGHT = 52
        START_USING_ITEM = 53
        IS_CAMERA_RELATIVE_MOVEMENT_ENABLED_DEPRECATED = 54
        IS_ROT_CONTROLLED_BY_MOVE_DIRECTION_DEPRECATED = 55
        START_SPIN_ATTACK = 56
        STOP_SPIN_ATTACK = 57
        IS_HOTBAR_ONLY_TOUCH = 58
        JUMP_RELEASED_RAW = 59
        JUMP_PRESSED_RAW = 60
        JUMP_CURRENT_RAW = 61
        SNEAK_RELEASED_RAW = 62
        SNEAK_PRESSED_RAW = 63
        SNEAK_CURRENT_RAW = 64
        INTERNAL_UPDATE = 65
        INPUT_NUM = auto()

    rot: Vec2
    pos: Vec3
    move: Vec2
    y_head_rot: float
    _true_1: Literal[True]
    input_data: bitset[InputData.INPUT_NUM]
    input_mode: InputMode
    play_mode: ClientPlayMode
    new_interaction_model: NewInteractionModel
    interact_rotation: Vec2
    client_tick: PlayerInputTick
    pos_delta: Vec3
    _true_2: Literal[True]
    item_use_transaction: PackedItemUseLegacyInventoryTransaction | None
    _true_3: Literal[True]
    item_stack_request: ItemStackRequestCereal.RequestData | None
    _true_4: Literal[True]
    player_block_actions: list[PlayerBlockActionData] | None
    _true_5: Literal[True]
    vehicle_rot: Vec2 | None
    _true_6: Literal[True]
    client_predicted_vehicle: ActorUniqueID | None
    analog_move_vector: Vec2
    camera_orientation: Vec3
    raw_move_vector: Vec2


@packet(id=36)
class PlayerActionPacket:
    runtime_id: ActorRuntimeID
    action: PlayerActionType
    pos: BlockPos
    result_pos: BlockPos
    face: varint32
