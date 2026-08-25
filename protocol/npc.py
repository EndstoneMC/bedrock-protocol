from enum import IntEnum

from protocol import packet, uint8
from protocol.actor import ActorRuntimeID

package = "bedrock.protocol"


@packet(id=98, since=2168)
class NpcRequestPacket:
    class RequestType(IntEnum, uint8):
        SET_ACTIONS = 0
        EXECUTE_ACTION = 1
        EXECUTE_CLOSING_COMMANDS = 2
        SET_NAME = 3
        SET_SKIN = 4
        SET_INTERACT_TEXT = 5
        EXECUTE_OPENING_COMMANDS = 6

    id: ActorRuntimeID
    type: RequestType
    actions: str
    action_index: uint8
    scene_name: str
