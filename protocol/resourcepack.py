from protocol._dsl import field, packet
from protocol.common import uint8, uint16

package = "bedrock.protocol"


@packet(id=8)
class ResourcePackClientResponsePacket:
    """Client reply to the server's resource-pack offer. `response` is the
    action code and `downloading_packs` names the packs it still needs."""

    response: uint8
    downloading_packs: list[str] = field(prefix=uint16)
