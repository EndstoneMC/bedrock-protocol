from protocol import packet
from protocol.actor import ActorUniqueID

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
