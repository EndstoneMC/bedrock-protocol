"""Versionless primitives shared across domains, from SharedTypes/versionless/.

Vec2, Vec3, BlockPos, Color, DimensionType, and world/level/block/'s BlockRuntimeId.
"""

from protocol import uvarint32, varint32

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"
go_package = "github.com/EndstoneMC/bedrock-protocol/go/protocol"


type BlockRuntimeId = uvarint32
type DimensionType = varint32


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


class Color:
    r: float
    g: float
    b: float
    a: float
