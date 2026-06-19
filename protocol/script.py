from enum import IntEnum

from protocol import field, packet, uint8
from protocol.actor import ActorUniqueID
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


@packet(id=150, since=407)
class CodeBuilderPacket:
    """Code Builder Packet"""

    url: str
    should_open_code_builder: bool


class CodeBuilderStorageQueryOptionsOperation(IntEnum):
    NONE = 0
    GET = 1
    SET = 2
    RESET = 3


class CodeBuilderStorageQueryOptionsCategory(IntEnum):
    NONE = 0
    CODE_STATUS = 1
    INSTANTIATION = 2


class CodeBuilderExecutionStateCodeStatus(IntEnum):
    NONE = 0
    NOT_STARTED = 1
    IN_PROGRESS = 2
    PAUSED = 3
    ERROR = 4
    SUCCEEDED = 5


@packet(id=178, since=486)
class CodeBuilderSourcePacket:
    """This is EDU exclusive, used in getInterface() of WebviewSystem."""

    operation: CodeBuilderStorageQueryOptionsOperation = field(type=uint8)
    category: CodeBuilderStorageQueryOptionsCategory = field(type=uint8)
    # Removed at v685, field name from CloudburstMC (pre-v776, BDS-invisible).
    value: str = field(until=685)
    code_status: CodeBuilderExecutionStateCodeStatus = field(type=uint8, since=685)


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
    # TODO: protocol-docs and bedrock-headers say the body is two strings (raw_variant_name + raw_variant_data),
    # but gophertunnel and CloudburstMC marshal a single network-little-endian CompoundTag here. Modelling as the
    # latter.
    payload: CompoundTag


# ScriptCustomEventPacket (id=117, until=594) is omitted: lone @packet(until=)
# is not expressible in the DSL today, and the body is fully removed long
# before v975. The id is unused on v975.


@packet(id=177, since=486)
class ScriptMessagePacket:
    """Used to send custom messages between client and server."""

    message_id: str
    message_value: str
