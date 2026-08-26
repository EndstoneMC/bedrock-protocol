from enum import IntEnum

from protocol import field, int32, packet, uint8
from protocol.actor import ActorRuntimeID

package = "bedrock.protocol"


class AgentAnimation(IntEnum, uint8):
    ARM_SWING = 0
    SHRUG = 1


@packet(id=304, since=2168)
class AgentAnimationPacket:
    anim: AgentAnimation
    runtime_id: ActorRuntimeID


class AgentActionType(IntEnum):
    ATTACK = 1
    COLLECT = 2
    DESTROY = 3
    DETECT_REDSTONE = 4
    DETECT_OBSTACLE = 5
    DROP = 6
    DROP_ALL = 7
    INSPECT = 8
    INSPECT_DATA = 9
    INSPECT_ITEM_COUNT = 10
    INSPECT_ITEM_DETAIL = 11
    INSPECT_ITEM_SPACE = 12
    INTERACT = 13
    MOVE = 14
    PLACE_BLOCK = 15
    TILL = 16
    TRANSFER_ITEM_TO = 17
    TURN = 18


@packet(id=181, since=2168)
class AgentActionEventPacket:
    request_id: str
    action: AgentActionType = field(type=int32)
    response: str
