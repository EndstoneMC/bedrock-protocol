import uuid
from enum import IntEnum

from protocol import field, packet, uint8, uint32, varint64
from protocol.common import Color, Vec2, Vec3
from protocol.level import DimensionType

package = "bedrock.protocol"


class WorldPosition:
    pos: Vec3
    dimension_type: DimensionType


class WaypointGroupAction(IntEnum):
    NONE = 0
    ADD = 1
    REMOVE = 2
    UPDATE = 3


class ServerWaypointPayload:
    update_flag: uint32
    is_visible: bool | None
    world_position: WorldPosition | None
    texture_path: str | None
    icon_size: Vec2 | None
    color: Color | None
    client_position_authority: bool | None
    actor_id: varint64 | None


class LocatorBarWaypointPayload:
    handle: uuid.UUID
    payload: ServerWaypointPayload
    action: WaypointGroupAction = field(type=uint8)


@packet(id=341, since=944)
class LocatorBarPacket:
    waypoints: list[LocatorBarWaypointPayload]
