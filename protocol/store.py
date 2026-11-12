"""Marketplace: store/ -- profile, store offers, receipts, entitlements."""

import uuid
from enum import IntEnum

from protocol import field, packet, sentinel, uint8
from protocol.presence import ClientStoreEntryPointConfiguration

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"


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
    offer_id: uuid.UUID = field(type=str, until=859)
    offer_id: uuid.UUID = field(since=859)
    redirect_type: ShowStoreOfferRedirectType


@packet(id=92)
class PurchaseReceiptPacket:
    purchase_receipts: list[str]


@packet(id=346, since=975)
class ServerStoreInfoPacket:
    client_store_entry_point_configuration: ClientStoreEntryPointConfiguration | None
