from enum import IntEnum

from protocol import field, int64, packet, uint8, varint32
from protocol.actor import ActorRuntimeID, ActorUniqueID

package = "bedrock.protocol"


@packet(id=169, since=448)
class NpcDialoguePacket:
    """Sent from the server to client when remote firing an NPC dialogue window for a client."""

    class NpcDialogueActionType(IntEnum):
        OPEN = 0
        CLOSE = 1

    npc_id: ActorUniqueID = field(type=int64)
    npc_dialogue_action_type: NpcDialogueActionType = field(type=varint32)
    dialogue: str
    scene_name: str
    npc_name: str
    action_json: str


@packet(id=98)
class NpcRequestPacket:
    """Used for a number of interactions with the NPC Component."""

    class RequestType(IntEnum):
        SET_ACTIONS = 0
        EXECUTE_ACTION = 1
        EXECUTE_CLOSING_COMMANDS = 2
        SET_NAME = 3
        SET_SKIN = 4
        SET_INTERACT_TEXT = 5
        EXECUTE_OPENING_COMMANDS = 6

    id: ActorRuntimeID
    type: RequestType = field(type=uint8)
    actions: str
    action_index: uint8
    scene_name: str = field(since=448)
