from enum import IntEnum

from protocol import field, packet, uint8, uint16
from protocol.actor import ActorUniqueID

package = "bedrock.protocol"


class BossEventUpdateType(IntEnum, uint8):
    ADD = 0
    PLAYER_ADDED = 1
    REMOVE = 2
    PLAYER_REMOVED = 3
    UPDATE_PERCENT = 4
    UPDATE_NAME = 5
    UPDATE_PROPERTIES = 6
    UPDATE_STYLE = 7
    QUERY = 8


class BossBarColor(IntEnum, uint8):
    PINK = 0
    BLUE = 1
    RED = 2
    GREEN = 3
    YELLOW = 4
    PURPLE = 5
    REBECCA_PURPLE = 6
    WHITE = 7


class BossBarOverlay(IntEnum, uint8):
    PROGRESS = 0
    NOTCHED_6 = 1
    NOTCHED_10 = 2
    NOTCHED_12 = 3
    NOTCHED_20 = 4


@packet(id=74, until=1001)
class BossEventPacket:
    """Sent when a boss gets updated"""

    boss_id: ActorUniqueID
    event_type: BossEventUpdateType

    player_id: ActorUniqueID = field(
        when=lambda p: (
            p.event_type
            in {BossEventUpdateType.PLAYER_ADDED, BossEventUpdateType.PLAYER_REMOVED, BossEventUpdateType.QUERY}
        )
    )

    with field(when=lambda p: p.event_type in {BossEventUpdateType.ADD, BossEventUpdateType.UPDATE_NAME}):
        name: str
        filtered_name: str

    health_percent: float = field(
        when=lambda p: p.event_type in {BossEventUpdateType.ADD, BossEventUpdateType.UPDATE_PERCENT}
    )
    darken_screen: uint16 = field(
        when=lambda p: p.event_type in {BossEventUpdateType.ADD, BossEventUpdateType.UPDATE_PROPERTIES}
    )

    with field(
        when=lambda p: (
            p.event_type
            in {BossEventUpdateType.ADD, BossEventUpdateType.UPDATE_PROPERTIES, BossEventUpdateType.UPDATE_STYLE}
        )
    ):
        color: BossBarColor
        overlay: BossBarOverlay


@packet(id=74, since=1001)
class BossEventPacket:
    """Sent when a boss gets updated"""

    boss_id: ActorUniqueID
    player_id: ActorUniqueID
    event_type: BossEventUpdateType
    name: str
    filtered_name: str
    health_percent: float
    color: BossBarColor
    overlay: BossBarOverlay
