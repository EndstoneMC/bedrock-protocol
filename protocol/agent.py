from enum import IntEnum

from protocol import field, int32, packet, type, uint8
from protocol.actor import ActorRuntimeID

package = "bedrock.protocol"

class AgentCapabilities:
    can_modify_blocks: bool | None


@type(since=503)
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


@packet(id=181, since=503)
class AgentActionEventPacket:
    """packet containing data of Agent Action Type"""

    request_id: str
    action: AgentActionType = field(type=int32)
    response: str


class AgentAnimation(IntEnum):
    ARM_SWING = 0
    SHRUG = 1


@packet(id=304, since=594)
class AgentAnimationPacket:
    """Broadcasted to other players when an Agent performs an animation so it gets properly replicated."""

    anim: AgentAnimation = field(type=uint8)
    runtime_id: ActorRuntimeID
