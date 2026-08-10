from enum import IntEnum, auto

from protocol import value

package = "bedrock.protocol"


class MovementEffectType(IntEnum):
    INVALID = -1
    GLIDE_BOOST = 0
    DOLPHIN_BOOST = 1
    GEYSER_BOOST = value(2, since=1001)
    COUNT = auto()
