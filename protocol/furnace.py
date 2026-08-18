from enum import IntEnum

from protocol import packet, type, uint8

package = "bedrock.protocol"


@type(since=2192)
class FurnaceLeftTabIndex(IntEnum):
    NONE = 0
    RECIPE_FOOD = 1
    RECIPE_ITEMS = 2
    RECIPE_BLOCKS = 3
    RECIPE_SEARCH = 4
    INVENTORY = 5


@type(since=2192)
class FurnaceLayout(IntEnum):
    NONE = 0
    INVENTORY_ONLY = 1
    DEFAULT = 2


@type(since=2192)
class FurnaceOptions:
    left_furnace_tab: FurnaceLeftTabIndex
    filtering: bool
    layout: FurnaceLayout


@packet(id=351, since=2192)
class SetPlayerFurnaceOptionsPacket:
    """The player's screen options for one kind of furnace: which left-hand tab is
    open, whether the recipe list is filtered, and the layout it draws with."""

    class FurnaceType(IntEnum, uint8):
        NONE = 0
        FURNACE = 1
        BLAST_FURNACE = 2
        SMOKER = 3

    furnace_type: FurnaceType
    furnace_options: FurnaceOptions
