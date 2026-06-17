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


@type(until=1001)
class SubChunkPos:
    x: varint32
    y: varint32
    z: varint32


# v1001 (cereal migration): the three coords moved from zigzag varint to a
# fixed little-endian int32 each. bedrock-headers (v975) confirms the field is
# a SubChunkPos in both eras (SubChunkRequestPacket::mCenterPos), and
# protocol-docs r26_u3 defines SubChunkPos as 3x int32 -- so this is a
# wire-format change of the same type, not a type swap.
@type(since=1001)
class SubChunkPos:  # noqa: F811
    x: int32
    y: int32
    z: int32


type Color = int32


class TintMapColor:
    colors: tuple[Color, Color, Color, Color]


# Cereal writes SharedTypes::Color255RGBA as a tagged union over a CSS-style
# hex string or a raw four-int RGBA array; the BDS struct itself is one
# `mce::Color { float r, g, b, a; }` wrapper.
type Color255RGBA = str | tuple[int32, int32, int32, int32]
