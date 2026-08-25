from enum import IntEnum

from protocol import packet, uint8, varint32
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


class PositionTrackingId:
    raw_id: varint32


@packet(id=153, since=2168)
class PositionTrackingDBServerBroadcastPacket:
    class Action(IntEnum, uint8):
        UPDATE = 0
        DESTROY = 1
        NOT_FOUND = 2

    action: Action
    id: PositionTrackingId
    data: CompoundTag


@packet(id=154, since=2168)
class PositionTrackingDBClientRequestPacket:
    class Action(IntEnum, uint8):
        QUERY = 0

    action: Action
    id: PositionTrackingId
