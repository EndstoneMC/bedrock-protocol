"""Versionless primitives shared across domains, the tier below every domain module:
SharedTypes/versionless/ -- Vec2, Vec3, BlockPos, Color, DimensionType -- and
world/level/block/'s BlockRuntimeId, which item.py needs and block.py would reach in a cycle.
Admission needs a primitive at the versionless root with two or more domain consumers,
or one whose own domain module cannot be imported by its consumers."""

from protocol import int32, uvarint32, varint32

package = "bedrock.protocol"


type BlockRuntimeId = uvarint32
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
