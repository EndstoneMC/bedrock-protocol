"""The scripting surface: scripting/ -- script messages and the primitive debug shapes
ScriptModuleMinecraft exposes."""

from enum import IntEnum, auto

from protocol import field, packet, type, uint8, uint16, uvarint64, value
from protocol.actor import ActorRuntimeID, ActorUniqueID
from protocol.common import Color, DimensionType, Vec2, Vec3

package = "bedrock.protocol"


@packet(id=177)
class ScriptMessagePacket:
    message_id: str
    message_value: str


@packet(id=64)
class SimpleEventPacket:
    class Subtype(IntEnum, uint16):
        UNINITIALIZED_SUBTYPE = 0
        ENABLE_COMMANDS = 1
        DISABLE_COMMANDS = 2
        UNLOCK_WORLD_TEMPLATE_SETTINGS = 3

    subtype: Subtype = field(type=uint16)


class ScriptPrimitiveShapeType(IntEnum, uint8):
    LINE = 0
    BOX = 1
    SPHERE = 2
    CIRCLE = 3
    TEXT = 4
    ARROW = 5
    CYLINDER = value(6, since=1001)
    PYRAMID = value(7, since=1001)
    ELLIPSOID = value(8, since=1001)
    CONE = value(9, since=1001)
    NUM_SHAPE_TYPES = auto()


class ArrowDataPayload:
    end_location: Vec3 | None
    arrow_head_length: float | None
    arrow_head_radius: float | None
    num_segments: uint8 | None


class TextDataPayload:
    text: str
    use_rotation: bool = field(since=975)
    background_color: Color | None = field(since=975)
    line_gap_height: float = field(since=2192)
    depth_test: bool = field(since=975)
    show_backface: bool = field(since=975)
    show_text_backface: bool = field(since=975)


class BoxDataPayload:
    box_bound: Vec3


class LineDataPayload:
    end_location: Vec3


class SphereDataPayload:
    num_segments: uint8


@type(since=1001)
class CylinderDataPayload:
    radius_x: Vec2
    radius_z: Vec2
    height: float
    num_segments: uint8


@type(since=1001)
class PyramidDataPayload:
    width: float
    depth: float | None
    height: float


@type(since=1001)
class EllipsoidDataPayload:
    radii: Vec3
    segments_per_axis: uint8


@type(since=1001)
class ConeDataPayload:
    radii: Vec2
    height: float
    num_segments: uint8


@type(until=859)
class PacketShapeData:
    """Wire shape mirrors ScriptModuleMinecraft::ScriptPrimitiveShape::populatePacketData.
    Most fields are gated by per-instance dirty flags on the server, so they ride as
    optionals."""

    network_id: uvarint64
    shape_type: ScriptPrimitiveShapeType | None
    location: Vec3 | None
    scale: float | None
    rotation: Vec3 | None
    time_left_total_sec: float | None
    color: Color | None
    text: str | None
    box_bound: Vec3 | None
    end_location: Vec3 | None
    arrow_head_length: float | None
    arrow_head_radius: float | None
    num_segments: uint8 | None


@type(since=859, until=898)
class PrimitiveShapeDataPayload:
    network_id: uvarint64
    shape_type: ScriptPrimitiveShapeType | None
    location: Vec3 | None
    scale: float | None
    rotation: Vec3 | None
    time_left_total_sec: float | None
    color: Color | None
    dimension_id: DimensionType
    extra_data_payload: None | ArrowDataPayload | TextDataPayload | BoxDataPayload | LineDataPayload | SphereDataPayload


@type(since=898, until=975)
class PrimitiveShapeDataPayload:
    network_id: uvarint64
    shape_type: ScriptPrimitiveShapeType | None
    location: Vec3 | None
    scale: float | None
    rotation: Vec3 | None
    time_left_total_sec: float | None
    color: Color | None
    dimension_id: DimensionType | None
    attached_to_id: ActorRuntimeID | None = field(since=924)
    extra_data_payload: None | ArrowDataPayload | TextDataPayload | BoxDataPayload | LineDataPayload | SphereDataPayload


@type(since=975, until=1001)
class PrimitiveShapeDataPayload:
    network_id: uvarint64
    shape_type: ScriptPrimitiveShapeType | None
    location: Vec3 | None
    scale: float | None
    rotation: Vec3 | None
    time_left_total_sec: float | None
    max_render_distance: float | None
    color: Color | None
    dimension_id: DimensionType | None
    attached_to_id: ActorUniqueID | None
    extra_data_payload: None | ArrowDataPayload | TextDataPayload | BoxDataPayload | LineDataPayload | SphereDataPayload


@type(since=1001)
class PrimitiveShapeDataPayload:
    network_id: uvarint64
    shape_type: ScriptPrimitiveShapeType | None
    location: Vec3 | None
    scale: float | None
    rotation: Vec3 | None
    time_left_total_sec: float | None
    max_render_distance: float | None
    color: Color | None
    dimension_id: DimensionType | None
    attached_to_id: ActorUniqueID | None
    extra_data_payload: (
        None
        | ArrowDataPayload
        | TextDataPayload
        | BoxDataPayload
        | LineDataPayload
        | SphereDataPayload
        | CylinderDataPayload
        | PyramidDataPayload
        | EllipsoidDataPayload
        | ConeDataPayload
    )


@packet(id=328, since=818, until=859)
class ServerScriptDebugDrawerPacket:
    """Send primitive drawing shape info (from scripting) to the client for rendering."""

    shapes: list[PacketShapeData]


@packet(id=328, since=859, until=975)
class DebugDrawerPacket:
    """Send primitive drawing shape info (from scripting) to the client for rendering."""

    shapes: list[PrimitiveShapeDataPayload]


@packet(id=328, since=975)
class PrimitiveShapesPacket:
    """Send primitive drawing shape info (from scripting) to the client for rendering."""

    shapes: list[PrimitiveShapeDataPayload]
