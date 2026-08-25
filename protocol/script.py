from enum import IntEnum

from protocol import field, packet, uint16

package = "bedrock.protocol"


@packet(id=177, since=2168)
class ScriptMessagePacket:
    message_id: str
    message_value: str


@packet(id=64, since=2168)
class SimpleEventPacket:
    class Subtype(IntEnum, uint16):
        UNINITIALIZED_SUBTYPE = 0
        ENABLE_COMMANDS = 1
        DISABLE_COMMANDS = 2
        UNLOCK_WORLD_TEMPLATE_SETTINGS = 3

    subtype: Subtype = field(type=uint16)
