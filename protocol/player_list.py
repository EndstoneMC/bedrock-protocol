import uuid
from enum import IntEnum

from protocol import field, int32, packet, uint8
from protocol.actor import ActorUniqueID
from protocol.common import Color
from protocol.skin import SerializedSkinRef

package = "bedrock.protocol"


class PlayerListPacketType(IntEnum, uint8):
    ADD = 0
    REMOVE = 1


class BuildPlatform(IntEnum, int):
    UNKNOWN = -1
    GOOGLE = 1
    IOS = 2
    OSX = 3
    AMAZON = 4
    GEAR_VR_DEPRECATED = 5
    UWP_DEPRECATED = 7
    WIN32 = 8
    DEDICATED = 9
    TV_OS_DEPRECATED = 10
    SONY = 11
    NX = 12
    XBOX = 13
    WINDOWS_PHONE_DEPRECATED = 14
    LINUX = 15


class PlayerListPacketPayload:
    """Each entry carries its action twice: once as the variant index over the two
    payloads, then again as the payload's own member."""

    class RemoveEntry:
        action: PlayerListPacketType
        uuid: uuid.UUID

    class AddEntry:
        action: PlayerListPacketType
        uuid: uuid.UUID
        actor_unique_id: ActorUniqueID
        name: str
        xuid: str
        platform_online_id: str
        build_platform: BuildPlatform = field(type=int32)
        skin: SerializedSkinRef
        is_teacher: bool
        is_host: bool
        is_sub_client: bool
        color: Color


# TODO: the 1001 form is not modelled. It is one packet-level action byte, then one
# uvarint32 count, then either full entries or bare UUIDs, then -- for ADD only -- a
# trailing run of one bool per entry carrying the skin's trusted flag. Two blockers:
# the legacy PlayerListEntry::write embeds a pre-cereal skin whose shape differs from
# the cerealised SerializedSkinRef in protocol/skin.py, and the trailing bool run needs
# a list whose count is an earlier list's length, which field(count=) cannot express.
@packet(id=63, since=2168)
class PlayerListPacket:
    entries: list[PlayerListPacketPayload.RemoveEntry | PlayerListPacketPayload.AddEntry]
