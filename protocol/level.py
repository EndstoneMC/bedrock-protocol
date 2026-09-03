"""Level state that is not settings: world/level/clock/ world clocks and time markers,
and world/level/PositionTrackingId.h behind lodestone markers.
Not game rules or LevelSettings -- those are in game.py."""

from enum import IntEnum

from protocol import int32, packet, uint8, uvarint64, varint32
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


@packet(id=10)
class SetTimePacket:
    time: varint32


class SyncWorldClockStateData:
    clock_id: uvarint64
    time: varint32
    is_paused: bool


class TimeMarkerData:
    id: uvarint64
    name: str
    time: varint32
    period: int32 | None


class WorldClockData:
    id: uvarint64
    name: str
    time: varint32
    is_paused: bool
    time_markers: list[TimeMarkerData]


@packet(id=344, since=944)
class SyncWorldClocksPacket:
    class SyncStateData:
        clock_data: list[SyncWorldClockStateData]

    class InitializeRegistryData:
        clock_data: list[WorldClockData]

    class AddTimeMarkerData:
        clock_id: uvarint64
        time_markers: list[TimeMarkerData]

    class RemoveTimeMarkerData:
        clock_id: uvarint64
        time_marker_ids: list[uvarint64]

    data: SyncStateData | InitializeRegistryData | AddTimeMarkerData | RemoveTimeMarkerData


class PositionTrackingId:
    raw_id: varint32


@packet(id=153)
class PositionTrackingDBServerBroadcastPacket:
    class Action(IntEnum, uint8):
        UPDATE = 0
        DESTROY = 1
        NOT_FOUND = 2

    action: Action
    id: PositionTrackingId
    data: CompoundTag


@packet(id=154)
class PositionTrackingDBClientRequestPacket:
    class Action(IntEnum, uint8):
        QUERY = 0

    action: Action
    id: PositionTrackingId
