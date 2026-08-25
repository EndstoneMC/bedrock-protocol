import uuid
from enum import IntEnum, auto

from protocol import packet, uint8

package = "bedrock.protocol"


@packet(id=104, since=2168)
class ShowProfilePacket:
    player_xuid: str


@packet(id=305, since=2168)
class RefreshEntitlementsPacket:
    pass


class ShowStoreOfferRedirectType(IntEnum, uint8):
    MARKETPLACE_OFFER = 0
    DRESSING_ROOM_OFFER = 1
    THIRD_PARTY_SERVER_PAGE = 2
    COUNT = auto()


@packet(id=91, since=2168)
class ShowStoreOfferPacket:
    offer_id: uuid.UUID
    redirect_type: ShowStoreOfferRedirectType
