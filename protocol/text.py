from enum import IntEnum

from protocol import packet, uint8

package = "bedrock.protocol"


class TextPacketType(IntEnum, uint8):
    RAW = 0
    CHAT = 1
    TRANSLATE = 2
    POPUP = 3
    JUKEBOX_POPUP = 4
    TIP = 5
    SYSTEM_MESSAGE = 6
    WHISPER = 7
    ANNOUNCEMENT = 8
    TEXT_OBJECT_WHISPER = 9
    TEXT_OBJECT = 10
    TEXT_OBJECT_ANNOUNCEMENT = 11


@packet(id=9, since=2168)
class TextPacket:
    class MessageOnly:
        type: TextPacketType
        message: str

    class AuthorAndMessage:
        type: TextPacketType
        author: str
        message: str

    class MessageAndParams:
        type: TextPacketType
        message: str
        params: list[str]

    localize: bool
    body: MessageOnly | AuthorAndMessage | MessageAndParams
    xuid: str
    platform_id: str
    filtered_message: str | None
