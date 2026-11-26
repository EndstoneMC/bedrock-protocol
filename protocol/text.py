"""Chat, titles and toasts, from textobject/."""

from enum import IntEnum
from typing import Literal

from protocol import field, int32, packet, uint8, varint32

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"
go_package = "github.com/EndstoneMC/bedrock-protocol/go/protocol"


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


@packet(id=9, until=898)
class TextPacket:
    type: TextPacketType
    localize: bool
    author: str = field(
        when=lambda p: p.type in {TextPacketType.CHAT, TextPacketType.WHISPER, TextPacketType.ANNOUNCEMENT}
    )
    message: str
    params: list[str] = field(
        when=lambda p: p.type in {TextPacketType.TRANSLATE, TextPacketType.POPUP, TextPacketType.JUKEBOX_POPUP}
    )
    xuid: str
    platform_id: str
    filtered_message: str = field(since=685)


@packet(id=9, since=898)
class TextPacket:
    class MessageOnly:
        with field(until=924):
            _raw: Literal["raw"]
            _tip: Literal["tip"]
            _system_message: Literal["systemmessage"]
            _text_object_whisper: Literal["textobjectwhisper"]
            _text_object_announcement: Literal["textobjectannouncement"]
            _text_object: Literal["textobject"]

        type: TextPacketType
        message: str

    class AuthorAndMessage:
        with field(until=924):
            _chat: Literal["chat"]
            _whisper: Literal["whisper"]
            _announcement: Literal["announcement"]

        type: TextPacketType
        author: str
        message: str

    class MessageAndParams:
        with field(until=924):
            _translate: Literal["translate"]
            _popup: Literal["popup"]
            _jukebox_popup: Literal["jukeboxpopup"]

        type: TextPacketType
        message: str
        params: list[str]
        queue: bool = field(since=2259)

    localize: bool
    body: MessageOnly | AuthorAndMessage | MessageAndParams
    xuid: str
    platform_id: str
    filtered_message: str | None


@packet(id=361, since=2259)
class ChatPacket:
    class SignedChat:
        key_id: str
        sender_id: str
        message_id: str
        scan_text: str
        redacted_text: str
        author_name: str
        signature: str

    class ChatFormatting:
        name_prefix: str | None
        name_postfix: str | None
        message_prefix: str | None
        message_postfix: str | None

    signed_chat: SignedChat
    room_id: str | None
    formatting: ChatFormatting | None


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
    filtered_title_text: str = field(since=712)
