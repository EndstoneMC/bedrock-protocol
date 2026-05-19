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
    response: ResourcePackResponse = field(type=uint8)
    downloading_packs: list[str] = field(prefix=uint16)
