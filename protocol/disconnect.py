from enum import IntEnum
from typing import ClassVar


class DisconnectFailReason(IntEnum):
    UNKNOWN = 0
    CANT_CONNECT_NO_INTERNET = 1
    NO_PERMISSIONS = 2
    UNRECOVERABLE_ERROR = 3
    THIRD_PARTY_BLOCK = 4


class DisconnectPacketMessages:
    message: str
    filtered_message: str


class DisconnectPacket:
    """Sent from the server to a client to trigger a disconnection."""

    id: ClassVar[int] = 5
    reason: DisconnectFailReason
    messages: DisconnectPacketMessages | None
