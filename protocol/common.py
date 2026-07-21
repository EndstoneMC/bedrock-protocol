from protocol import int32, varint32

package = "bedrock.protocol"


# BDS mce::Color holds four floats; cereal binds it as one packed ARGB int32.
type Color = int32


class Vec2:
    x: float
    y: float


class Vec3:
    x: float
    y: float
    z: float


class BlockPos:
    x: varint32
    y: varint32
    z: varint32
