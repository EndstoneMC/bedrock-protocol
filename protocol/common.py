from protocol import field, int32, type, uvarint32, varint32

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


@type(deprecated=944)
class NetworkBlockPos:
    x: int32 = field(type=varint32)
    y: int32 = field(type=uvarint32)
    z: int32 = field(type=varint32)


class SubChunkPos:
    x: varint32
    y: varint32
    z: varint32


type Color = int32


class TintMapColor:
    colors: tuple[Color, Color, Color, Color]


# Cereal writes SharedTypes::Color255RGBA as a tagged union over a CSS-style
# hex string or a raw four-int RGBA array; the BDS struct itself is one
# `mce::Color { float r, g, b, a; }` wrapper.
type Color255RGBA = str | tuple[int32, int32, int32, int32]
