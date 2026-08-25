from enum import IntEnum

from protocol import field, int64, packet, uint8, uint64
from protocol.actor import ActorUniqueID

package = "bedrock.protocol"


@packet(id=171, since=2168)
class CreatePhotoPacket:
    id: ActorUniqueID = field(type=uint64)
    photo_name: str
    photo_item_name: str


class PhotoType(IntEnum, uint8):
    PORTFOLIO = 0
    PHOTO_ITEM = 1
    BOOK = 2


@packet(id=99, since=2168)
class PhotoTransferPacket:
    photo_name: str
    photo_data: str
    book_id: str
    type: PhotoType
    source_type: PhotoType
    owner_id: ActorUniqueID = field(type=int64)
    new_photo_name: str
