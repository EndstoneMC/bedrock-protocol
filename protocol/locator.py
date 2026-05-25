import uuid
from enum import IntEnum

from protocol import field, packet, uint8, uint32
from protocol.actor import ActorUniqueID
from protocol.common import Vec2, Vec3
from protocol.level import DimensionType

package = "bedrock.protocol"


class WorldPosition:
    pos: Vec3
    dimension_type: DimensionType


class WaypointAction(IntEnum):
    NONE = 0
    ADD = 1
    REMOVE = 2
    UPDATE = 3


class ServerWaypointPayload:
    update_flag: uint32
    is_visible: bool | None
    world_position: WorldPosition | None
    # v975 replaced the texture-id ordinal with a texture-path string and added
    # an icon-size Vec2 alongside it.
    texture_id: uint32 | None = field(until=975)
    texture_path: str | None = field(since=975)
    icon_size: Vec2 | None = field(since=975)
    color: uint32 | None  # ARGB packed mce::Color
    client_position_authority: bool | None
    actor_id: ActorUniqueID | None


class LocatorBarWaypointPayload:
    handle: uuid.UUID
    payload: ServerWaypointPayload
    action: WaypointAction = field(type=uint8)


@packet(id=341, since=944)
class LocatorBarPacket:
    """Syncs LocatorBar changes on the server with the client."""

    waypoints: list[LocatorBarWaypointPayload]
