from enum import IntEnum

from protocol import packet, uint8, uvarint32

package = "bedrock.protocol"


@packet(id=100, since=2168)
class ModalFormRequestPacket:
    form_id: uvarint32
    form_json: str


@packet(id=102, since=2168)
class ServerSettingsRequestPacket:
    pass


@packet(id=103, since=2168)
class ServerSettingsResponsePacket:
    """The server's answer to a settings request: the JSON describing a settings tab
    to draw for this server, and the form id the client echoes back when the player
    submits it."""

    form_id: uvarint32
    form_json: str


@packet(id=310, since=2168)
class ClientboundCloseFormPacket:
    pass


class ModalFormCancelReason(IntEnum, uint8):
    USER_CLOSED = 0
    USER_BUSY = 1


@packet(id=101, since=2168)
class ModalFormResponsePacket:
    form_id: uvarint32
    json_response: str | None
    form_cancel_reason: ModalFormCancelReason | None
