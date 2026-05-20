from protocol import int32, varint32

package = "bedrock.protocol"


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


class SubChunkPos:
    x: varint32
    y: varint32
    z: varint32


type Color = int32


class TintMapColor:
    colors: tuple[Color, Color, Color, Color]
