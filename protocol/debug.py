from enum import Enum

from protocol import field, packet, uint8, uint64
from protocol.actor import ActorUniqueID
from protocol.common import Color, Vec3

package = "bedrock.protocol"


@packet(id=190, since=2168)
class EditorNetworkPacket:
    route_to_manager: bool
    raw_variant_name: str
    raw_variant_data: str


@packet(id=155, since=2168)
class DebugInfoPacket:
    actor_id: ActorUniqueID
    data: str


@packet(id=164, since=2168)
class ClientboundDebugRendererPacket:
    class PayloadType(Enum, uint8):
        INVALID = 0
        CLEAR_DEBUG_MARKERS = 1, "ClearDebugMarkers"
        ADD_DEBUG_MARKER_CUBE = 2, "AddDebugMarkerCube"

    class DebugMarkerData:
        text: str
        position: Vec3
        color: Color
        duration_ms: uint64

    type: PayloadType = field(type=str)
    debug_marker_data: DebugMarkerData | None
