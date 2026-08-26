import uuid
from enum import Enum, IntEnum

from protocol import field, packet, uint8, uint32, uvarint64
from protocol.actor import ActorUniqueID
from protocol.attributes import DimensionType
from protocol.common import Color, Vec2, Vec3

package = "bedrock.protocol"


@packet(id=335, since=2168)
class ClientboundDataDrivenUIReloadPacket:
    pass


class HudElement(IntEnum):
    PAPER_DOLL = 0
    ARMOR = 1
    TOOL_TIPS = 2
    TOUCH_CONTROLS = 3
    CROSSHAIR = 4
    HOT_BAR = 5
    HEALTH = 6
    PROGRESS_BAR = 7
    HUNGER = 8
    AIR_BUBBLES = 9
    HORSE_HEALTH = 10
    STATUS_EFFECTS = 11
    ITEM_TEXT = 12


class HudVisibility(IntEnum):
    HIDE = 0
    RESET = 1


@packet(id=308, since=2168)
class SetHudPacket:
    hud_element: list[HudElement]
    hud_visible: HudVisibility


class ServerboundLoadingScreenPacketType(IntEnum):
    UNKNOWN = 0
    START_LOADING_SCREEN = 1
    END_LOADING_SCREEN = 2


@packet(id=312, since=2168)
class ServerboundLoadingScreenPacket:
    loading_screen_packet_type: ServerboundLoadingScreenPacketType
    loading_screen_id: uint32 | None


@packet(id=334, since=2168)
class ClientboundDataDrivenUICloseScreenPacket:
    form_id: uint32 | None


@packet(id=333, since=2168)
class ClientboundDataDrivenUIShowScreenPacket:
    screen_id: str
    form_id: uint32
    data_instance_id: uint32 | None


@packet(id=336, since=2168)
class ClientboundTextureShiftPacket:
    class Action(IntEnum, uint8):
        INVALID = 0
        INITIALIZE = 1
        START = 2
        SET_ENABLED = 3
        SYNC = 4

    action: Action
    collection_name: str
    from_step: str
    to_step: str
    all_steps: list[str]
    current_length_in_ticks: uvarint64
    total_length_in_ticks: uvarint64
    enabled: bool


class WorldPosition:
    pos: Vec3
    dimension_type: DimensionType


class WaypointGroup:
    class WaypointHandle:
        uuid: uuid.UUID


class ServerWaypoint:
    class Payload:
        update_flag: uint32
        is_visible: bool | None
        world_position: WorldPosition | None
        texture_path: str | None
        icon_size: Vec2 | None
        color: Color | None
        client_position_authority: bool | None
        actor_id: ActorUniqueID | None


class ServerWaypointGroup:
    class Action(IntEnum, uint8):
        NONE = 0
        ADD = 1
        REMOVE = 2
        UPDATE = 3


class LocatorBarWaypointPayload:
    handle: WaypointGroup.WaypointHandle
    payload: ServerWaypoint.Payload
    action: ServerWaypointGroup.Action


@packet(id=341, since=2168)
class LocatorBarPacket:
    waypoints: list[LocatorBarWaypointPayload]


class DataDrivenScreenClosedReason(Enum, uint8):
    PROGRAMMATIC_CLOSE = 0, "ProgrammaticClose"
    PROGRAMMATIC_CLOSE_ALL = 1, "ProgrammaticCloseAll"
    CLIENT_CANCELED = 2, "ClientCanceled"
    USER_BUSY = 3, "UserBusy"
    INVALID_FORM = 4, "InvalidForm"


@packet(id=343, since=2168)
class ServerboundDataDrivenScreenClosedPacket:
    form_id: uint32
    close_reason: DataDrivenScreenClosedReason = field(type=str)
