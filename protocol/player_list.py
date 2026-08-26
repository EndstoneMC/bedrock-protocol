import uuid
from enum import IntEnum

from protocol import field, int32, packet, type, uint8, value
from protocol.actor import ActorUniqueID
from protocol.common import Color
from protocol.skin import SerializedSkinRef

package = "bedrock.protocol"


class PlayerListPacketType(IntEnum, uint8):
    ADD = 0
    REMOVE = 1


class BuildPlatform(IntEnum):
    UNKNOWN = -1
    GOOGLE = 1
    IOS = 2
    OSX = 3
    AMAZON = 4
    GEAR_VR_DEPRECATED = 5
    UWP_DEPRECATED = 7
    WINDOWS = value(8, "Win32")
    DEDICATED = 9
    TV_OS_DEPRECATED = 10
    SONY = 11
    NINTENDO = 12
    XBOX = 13
    WINDOWS_PHONE_DEPRECATED = 14
    LINUX = 15


@type(until=2168)
class PlayerListEntry:
    uuid: uuid.UUID
    id: ActorUniqueID
    name: str
    xuid: str
    platform_online_id: str
    build_platform: BuildPlatform = field(type=int32)
    skin: SerializedSkinRef = field(cereal=False)
    is_teacher: bool
    is_host: bool
    is_sub_client: bool
    color: Color


@packet(id=63, until=2168)
class PlayerListPacket:
    action: PlayerListPacketType
    entries: list[PlayerListEntry] = field(when=lambda p: p.action == PlayerListPacketType.ADD)
    removed_entries: list[uuid.UUID] = field(when=lambda p: p.action == PlayerListPacketType.REMOVE)
    trusted_skins: list[bool] = field(
        when=lambda p: p.action == PlayerListPacketType.ADD,
        count=lambda p: len(p.entries),
    )


@packet(id=63, since=2168)
class PlayerListPacket:
    """Each entry carries its action twice: once as the variant index over the two
    payloads, then again as the payload's own member."""

    class RemoveEntry:
        action: PlayerListPacketType
        uuid: uuid.UUID

    class AddEntry:
        action: PlayerListPacketType
        uuid: uuid.UUID
        id: ActorUniqueID
        name: str
        xuid: str
        platform_online_id: str
        build_platform: BuildPlatform = field(type=int32)
        skin: SerializedSkinRef
        is_teacher: bool
        is_host: bool
        is_sub_client: bool
        color: Color

    entries: list[RemoveEntry | AddEntry]
