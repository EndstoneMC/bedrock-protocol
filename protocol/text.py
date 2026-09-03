"""Chat, titles and toasts: textobject/."""

from enum import IntEnum

from protocol import packet, uint8, varint32

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


@packet(id=9)
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


@packet(id=186)
class ToastRequestPacket:
    title: str
    content: str


@packet(id=88)
class SetTitlePacket:
    class TitleType(IntEnum):
        CLEAR = 0
        RESET = 1
        TITLE = 2
        SUBTITLE = 3
        ACTIONBAR = 4
        TIMES = 5
        TITLE_TEXT_OBJECT = 6
        SUBTITLE_TEXT_OBJECT = 7
        ACTIONBAR_TEXT_OBJECT = 8

    type: TitleType
    title_text: str
    fade_in_time: varint32
    stay_time: varint32
    fade_out_time: varint32
    xuid: str
    platform_online_id: str
    filtered_title_text: str
