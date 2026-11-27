"""Packets and types relating to the marketplace."""

import uuid
from enum import IntEnum

from protocol import field, packet, sentinel, uint8
from protocol.presence import ClientStoreEntryPointConfiguration

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"
go_package = "github.com/EndstoneMC/bedrock-protocol/go/protocol"


@packet(id=104)
class ShowProfilePacket:
    player_xuid: str


@packet(id=305)
class RefreshEntitlementsPacket:
    pass


class ShowStoreOfferRedirectType(IntEnum, uint8):
    MARKETPLACE_OFFER = 0
    DRESSING_ROOM_OFFER = 1
    THIRD_PARTY_SERVER_PAGE = 2
    COUNT = sentinel()


@packet(id=91)
class ShowStoreOfferPacket:
    offer_id: str = field(until=859)
    offer_id: uuid.UUID = field(since=859)
    show_all: bool = field(until=630)
    redirect_type: ShowStoreOfferRedirectType = field(since=630)


@packet(id=92)
class PurchaseReceiptPacket:
    purchase_receipts: list[str]


@packet(id=346, since=975)
class ServerStoreInfoPacket:
    client_store_entry_point_configuration: ClientStoreEntryPointConfiguration | None
