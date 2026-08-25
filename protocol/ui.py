from enum import IntEnum

from protocol import packet, uint32

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
