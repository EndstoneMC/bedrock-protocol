"""Versionless primitives shared across domains, the tier below every domain module:
SharedTypes/versionless/ -- Vec2, Vec3, BlockPos, Color, DimensionType.
Admission needs a primitive at the versionless root with two or more domain consumers."""

from protocol import int32, varint32

package = "bedrock.protocol"


type Color = int32
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
