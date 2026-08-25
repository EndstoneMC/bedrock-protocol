import uuid
from enum import IntEnum

from protocol import packet, uint8, uvarint32
from protocol.actor import ActorRuntimeID

package = "bedrock.protocol"


@packet(id=138, since=2168)
class EmotePacket:
    class Flags(IntEnum, uint8):
        SERVER_SIDE = 1
        MUTE_EMOTE_CHAT = 2

    runtime_id: ActorRuntimeID
    piece_id: str
    emote_ticks: uvarint32
    xuid: str
    platform_id: str
    flags: uint8


@packet(id=152, since=2168)
class EmoteListPacket:
    runtime_id: ActorRuntimeID
    emote_piece_ids: list[uuid.UUID]
