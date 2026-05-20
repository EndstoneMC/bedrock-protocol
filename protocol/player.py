from enum import IntEnum

from protocol import bitset, field, packet, type, uvarint32, uvarint64, value
from protocol.actor import ActorUniqueID
from protocol.common import Vec2, Vec3

package = "bedrock.protocol"

type PlayerInputTick = uvarint64


class InputMode(IntEnum):
    UNDEFINED = 0
    MOUSE = 1
    TOUCH = 2
    GAME_PAD = 3
    MOTION_CONTROLLER = value(4, deprecated=True)
    COUNT = 5


class ClientPlayMode(IntEnum):
    NORMAL = 0
    TEASER = 1
    SCREEN = 2
    VIEWER = value(3, deprecated=True)
    REALITY = value(4, deprecated=True)
    PLACEMENT = value(5, deprecated=True)
    LIVING_ROOM = value(6, deprecated=True)
    EXIT_LEVEL = 7
    EXIT_LEVEL_LIVING_ROOM = value(8, deprecated=True)
    NUM_MODES = 9


@type(since=527)
class NewInteractionModel(IntEnum):
    TOUCH = 0
    CROSSHAIR = 1
    CLASSIC = 2
    COUNT = 3


@packet(id=144, since=388)
class PlayerAuthInputPacket:
    class InputData(IntEnum):
        ASCEND = 0
        DESCEND = 1
        NORTH_JUMP = value(2, deprecated=True)
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
        IS_CAMERA_RELATIVE_MOVEMENT_ENABLED = value(54, since=748, deprecated=True)
        IS_ROT_CONTROLLED_BY_MOVE_DIRECTION = value(55, since=748, deprecated=True)
        START_SPIN_ATTACK = value(56, since=748)
        STOP_SPIN_ATTACK = value(57, since=748)
        IS_HOTBAR_ONLY_TOUCH = value(58, since=766)
        JUMP_RELEASED_RAW = value(59, since=766)
        JUMP_PRESSED_RAW = value(60, since=766)
        JUMP_CURRENT_RAW = value(61, since=766)
        SNEAK_RELEASED_RAW = value(62, since=766)
        SNEAK_PRESSED_RAW = value(63, since=766)
        SNEAK_CURRENT_RAW = value(64, since=766)
        INPUT_NUM = value(sentinel=True)

    rot: Vec2
    pos: Vec3
    move: Vec2
    y_head_rot: float
    input_data: bitset[InputData.INPUT_NUM]
    input_mode: InputMode = field(type=uvarint32)
    play_mode: ClientPlayMode = field(type=uvarint32)
    new_interaction_model: NewInteractionModel = field(type=uvarint32, since=527)
    interact_rotation: Vec2 = field(since=748)
    client_tick: PlayerInputTick = field(since=419)
    pos_delta: Vec3 = field(since=419)
    with field(
        when=lambda p: p.input_data.test(InputData.IS_IN_CLIENT_PREDICTED_VEHICLE)
    ):
        vehicle_rot: Vec2 = field(since=662)
        client_predicted_vehicle: ActorUniqueID = field(since=649)
    analog_move_vector: Vec2 = field(since=575)
    camera_orientation: Vec3 = field(since=748)
    raw_move_vector: Vec2 = field(since=766)
