from protocol import field, packet, uint64
from protocol.actor import ActorUniqueID

package = "bedrock.protocol"


@packet(id=171, since=2168)
class CreatePhotoPacket:
    id: ActorUniqueID = field(type=uint64)
    photo_name: str
    photo_item_name: str
