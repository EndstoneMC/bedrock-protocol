from enum import IntEnum

from protocol import packet, uint8
from protocol.actor import ActorRuntimeID

package = "bedrock.protocol"


class AgentAnimation(IntEnum, uint8):
    ARM_SWING = 0
    SHRUG = 1


@packet(id=304, since=2168)
class AgentAnimationPacket:
    anim: AgentAnimation
    runtime_id: ActorRuntimeID
