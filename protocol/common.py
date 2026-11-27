"""Types shared across the protocol."""

from enum import IntEnum

from protocol import int32, uint32, uvarint32, varint32

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


class EasingType(IntEnum, uint32):
    LINEAR = 0
    SPRING = 1
    IN_QUAD = 2, "in_quad"
    OUT_QUAD = 3, "out_quad"
    IN_OUT_QUAD = 4, "in_out_quad"
    IN_CUBIC = 5, "in_cubic"
    OUT_CUBIC = 6, "out_cubic"
    IN_OUT_CUBIC = 7, "in_out_cubic"
    IN_QUART = 8, "in_quart"
    OUT_QUART = 9, "out_quart"
    IN_OUT_QUART = 10, "in_out_quart"
    IN_QUINT = 11, "in_quint"
    OUT_QUINT = 12, "out_quint"
    IN_OUT_QUINT = 13, "in_out_quint"
    IN_SINE = 14, "in_sine"
    OUT_SINE = 15, "out_sine"
    IN_OUT_SINE = 16, "in_out_sine"
    IN_EXPO = 17, "in_expo"
    OUT_EXPO = 18, "out_expo"
    IN_OUT_EXPO = 19, "in_out_expo"
    IN_CIRC = 20, "in_circ"
    OUT_CIRC = 21, "out_circ"
    IN_OUT_CIRC = 22, "in_out_circ"
    IN_BOUNCE = 23, "in_bounce"
    OUT_BOUNCE = 24, "out_bounce"
    IN_OUT_BOUNCE = 25, "in_out_bounce"
    IN_BACK = 26, "in_back"
    OUT_BACK = 27, "out_back"
    IN_OUT_BACK = 28, "in_out_back"
    IN_ELASTIC = 29, "in_elastic"
    OUT_ELASTIC = 30, "out_elastic"
    IN_OUT_ELASTIC = 31, "in_out_elastic"


class Color255RGBA:
    r: int32
    g: int32
    b: int32
    a: int32


class WorldPosition:
    pos: Vec3
    dimension_type: DimensionType
