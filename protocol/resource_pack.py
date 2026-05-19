from enum import IntEnum

from protocol._dsl import field, packet
from protocol.common import uint8, uint16

package = "bedrock.protocol"


class ResourcePackResponse(IntEnum):
    CANCEL = 1
    DOWNLOADING = 2
    DOWNLOADING_FINISHED = 3
    RESOURCE_PACK_STACK_FINISHED = 4


@packet(id=8)
class ResourcePackClientResponsePacket:
    """Client reply to the server's resource-pack offer. `response` is the
    action code and `downloading_packs` names the packs it still needs."""

    response: ResourcePackResponse = field(type=uint8)
    downloading_packs: list[str] = field(prefix=uint16)
