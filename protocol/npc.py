from enum import IntEnum

from protocol import field, packet, uint8, uint64
from protocol.actor import ActorRuntimeID, ActorUniqueID

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


@packet(id=169, since=2168)
class NpcDialoguePacket:
    class NpcDialogueActionType(IntEnum):
        OPEN = 0
        CLOSE = 1

    npc_id: ActorUniqueID = field(type=uint64)
    npc_dialogue_action_type: NpcDialogueActionType
    dialogue: str
    scene_name: str
    npc_name: str
    action_json: str
