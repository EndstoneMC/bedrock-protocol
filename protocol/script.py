from protocol import field, packet
from protocol.actor import ActorUniqueID
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


@packet(id=155, since=407)
class DebugInfoPacket:
    """The system sends debug information via a generic network packet. This enables rendering of any server
    information on the client in for instance ImGui."""

    actor_id: ActorUniqueID
    data: str


@packet(id=190, since=534)
class EditorNetworkPacket:
    """General use Editor specific packet - carries a payload of whatever serialized data that the individual
    IEditorNetworkPayload generates."""

    route_to_manager: bool = field(since=712)
    payload: CompoundTag = field(until=1001)
    raw_variant_name: str = field(since=1001)
    raw_variant_data: str = field(since=1001)


# ScriptCustomEventPacket (id=117, until=594) is omitted: lone @packet(until=)
# is not expressible in the DSL today, and the body is fully removed long
# before v975. The id is unused on v975.


@packet(id=177, since=486)
class ScriptMessagePacket:
    """Used to send custom messages between client and server."""

    message_id: str
    message_value: str
