from protocol._dsl import field, packet
from protocol.common import int32

package = "bedrock.protocol"


@packet(id=1)
class LoginPacket:
    client_network_version: int32 = field(endian="big")
    connection_request: str
