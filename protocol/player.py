from enum import IntEnum

from protocol import packet, uint8
from protocol.actor import ActorRuntimeID
from protocol.common import Vec3

package = "bedrock.protocol"


class PlayerRespawnState(IntEnum, uint8):
    SEARCHING_FOR_SPAWN = 0
    READY_TO_SPAWN = 1
    CLIENT_READY_TO_SPAWN = 2


@packet(id=45, since=2168)
class RespawnPacket:
    pos: Vec3
    state: PlayerRespawnState
    runtime_id: ActorRuntimeID
