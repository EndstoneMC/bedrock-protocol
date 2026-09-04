"""Server-driven screens and HUD: dataDrivenUI/ plus world/Waypoint*.h and
util/HudElementsEnum.h -- modal forms, server settings, data-driven UI, HUD elements,
loading screens, texture shift, the locator bar."""

import uuid
from enum import Enum, IntEnum, auto

from protocol import field, packet, type, uint8, uint32, uvarint32, uvarint64
from protocol.actor import ActorUniqueID
from protocol.common import Color, DimensionType, Vec2, Vec3

package = "bedrock.protocol"


@packet(id=335, since=924)
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
    COUNT = auto()


class HudVisibility(IntEnum):
    HIDE = 0
    RESET = 1
    COUNT = auto()


@packet(id=308)
class SetHudPacket:
    hud_element: list[HudElement]
    hud_visible: HudVisibility


class ServerboundLoadingScreenPacketType(IntEnum):
    UNKNOWN = 0
    START_LOADING_SCREEN = 1
    END_LOADING_SCREEN = 2


@packet(id=312)
class ServerboundLoadingScreenPacket:
    loading_screen_packet_type: ServerboundLoadingScreenPacketType
    loading_screen_id: uint32 | None


@packet(id=334, since=924, until=944)
class ClientboundDataDrivenUICloseAllScreensPacket:
    pass


@packet(id=334, since=944)
class ClientboundDataDrivenUICloseScreenPacket:
    form_id: uint32 | None


@packet(id=333, since=924)
class ClientboundDataDrivenUIShowScreenPacket:
    screen_id: str
    form_id: uint32 = field(since=944)
    data_instance_id: uint32 | None = field(since=944)


@packet(id=336, since=924)
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
    @type(until=975)
    class Payload:
        update_flag: uint32
        is_visible: bool | None
        world_position: WorldPosition | None
        texture_id: uint32 | None
        color: Color | None
        client_position_authority: bool | None
        actor_id: ActorUniqueID | None

    @type(since=975)
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


@packet(id=341, since=944)
class LocatorBarPacket:
    waypoints: list[LocatorBarWaypointPayload]


class DataDrivenScreenClosedReason(Enum, uint8):
    PROGRAMMATIC_CLOSE = 0
    PROGRAMMATIC_CLOSE_ALL = 1
    CLIENT_CANCELED = 2
    USER_BUSY = 3
    INVALID_FORM = 4


@packet(id=343, since=944)
class ServerboundDataDrivenScreenClosedPacket:
    form_id: uint32
    close_reason: DataDrivenScreenClosedReason = field(type=str)


@packet(id=100)
class ModalFormRequestPacket:
    form_id: uvarint32
    form_json: str


@packet(id=102)
class ServerSettingsRequestPacket:
    pass


@packet(id=103)
class ServerSettingsResponsePacket:
    """The server's answer to a settings request: the JSON describing a settings tab
    to draw for this server, and the form id the client echoes back when the player
    submits it."""

    form_id: uvarint32
    form_json: str


@packet(id=310)
class ClientboundCloseFormPacket:
    pass


class ModalFormCancelReason(IntEnum, uint8):
    USER_CLOSED = 0
    USER_BUSY = 1


@packet(id=101)
class ModalFormResponsePacket:
    form_id: uvarint32
    json_response: str | None
    form_cancel_reason: ModalFormCancelReason | None


@packet(id=130)
class OnScreenTextureAnimationPacket:
    effect_id: uint32
