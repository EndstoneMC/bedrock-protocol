from enum import IntEnum

from protocol import uint8, value

package = "bedrock.protocol"


class MinecraftEventing:
    class InteractionType(IntEnum, uint8):
        BREEDING = 1
        TAMING = 2
        CURING = 3
        CRAFTED = 4
        SHEARING = 5
        MILKING = 6
        TRADING = 7
        FEEDING = 8
        IGNITING = 9
        COLORING = 10
        NAMING = 11
        LEASHING = 12
        UNLEASHING = 13
        PET_SLEEP = 14
        TRUSTING = 15
        COMMANDING = 16
        EQUIPPING = value(17, since=1001)
