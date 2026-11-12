"""Chat, titles and toasts: textobject/."""

from enum import IntEnum
from typing import Literal

from protocol import field, int32, packet, uint8, varint32

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
        with field(since=898, until=924):
            _raw: Literal["raw"]
            _tip: Literal["tip"]
            _system_message: Literal["systemmessage"]
            _text_object_whisper: Literal["textobjectwhisper"]
            _text_object_announcement: Literal["textobjectannouncement"]
            _text_object: Literal["textobject"]

        type: TextPacketType
        message: str

    class AuthorAndMessage:
        with field(since=898, until=924):
            _chat: Literal["chat"]
            _whisper: Literal["whisper"]
            _announcement: Literal["announcement"]

        type: TextPacketType
        author: str
        message: str

    class MessageAndParams:
        with field(since=898, until=924):
            _translate: Literal["translate"]
            _popup: Literal["popup"]
            _jukebox_popup: Literal["jukeboxpopup"]

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
    class TitleType(IntEnum, int32):
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
