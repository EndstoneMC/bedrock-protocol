"""Marketplace: store/ -- profile, store offers, receipts, entitlements."""

import uuid
from enum import IntEnum, auto

from protocol import packet, uint8
from protocol.presence import ClientStoreEntryPointConfiguration

package = "bedrock.protocol"


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
    COUNT = auto()


@packet(id=91)
class ShowStoreOfferPacket:
    offer_id: uuid.UUID
    redirect_type: ShowStoreOfferRedirectType


@packet(id=92)
class PurchaseReceiptPacket:
    purchase_receipts: list[str]


@packet(id=346)
class ServerStoreInfoPacket:
    client_store_entry_point_configuration: ClientStoreEntryPointConfiguration | None
