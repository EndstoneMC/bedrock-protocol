from protocol._dsl import field, packet
from protocol.common import int32

package = "bedrock.protocol"


@packet(id=193)
class RequestNetworkSettingsPacket:
    """This is the initial packet sent from the client to initiate a connection.

    NOTE: this packet should not contain anything other than the client version.
    """

    client_network_version: int32 = field(endian="big")
