from enum import IntEnum

from protocol import field, packet, type, uint8, uvarint64, value
from protocol.actor import ActorUniqueID
from protocol.common import Color, Vec3
from protocol.level import DimensionType

package = "bedrock.protocol"


@type(since=859)
class GraphicsOverrideParameterType(IntEnum):
    SKY_ZENITH_COLOR = 0
    SKY_HORIZON_COLOR = 1
    HORIZON_BLEND_MIN = 2
    HORIZON_BLEND_MAX = 3
    HORIZON_BLEND_START = 4
    HORIZON_BLEND_MIE_START = 5
    RAYLEIGH_STRENGTH = 6
    SUN_MIE_STRENGTH = 7
    MOON_MIE_STRENGTH = 8
    SUN_GLARE_SHAPE = 9
    CHLOROPHYLL = 10
    CDOM = 11
    SUSPENDED_SEDIMENT = 12
    WAVES_DEPTH = 13
    WAVES_FREQUENCY = 14
    WAVES_FREQUENCY_SCALING = 15
    WAVES_SPEED = 16
    WAVES_SPEED_SCALING = 17
    WAVES_SHAPE = 18
    WAVES_OCTAVES = 19
    WAVES_MIX = 20
    WAVES_PULL = 21
    WAVES_DIRECTION_INCREMENT = 22
    MIDTONES_CONTRAST = 23
    HIGHLIGHTS_CONTRAST = 24
    SHADOWS_CONTRAST = 25
    HIGHLIGHTS_GAIN = value(26, since=944)
    HIGHLIGHTS_GAMMA = value(27, since=944)
    HIGHLIGHTS_OFFSET = value(28, since=944)
    HIGHLIGHTS_SATURATION = value(29, since=944)
    MIDTONES_GAIN = value(30, since=944)
    MIDTONES_GAMMA = value(31, since=944)
    MIDTONES_OFFSET = value(32, since=944)
    MIDTONES_SATURATION = value(33, since=944)
    SHADOWS_GAIN = value(34, since=944)
    SHADOWS_GAMMA = value(35, since=944)
    SHADOWS_OFFSET = value(36, since=944)
    SHADOWS_SATURATION = value(37, since=944)
    HIGHLIGHTS_MIN = value(38, since=944)
    SHADOWS_MAX = value(39, since=944)
    TEMPERATURE = value(40, since=944)
    SUN_COLOR = value(41, since=944)
    SUN_ILLUMINANCE = value(42, since=944)
    MOON_COLOR = value(43, since=944)
    MOON_ILLUMINANCE = value(44, since=944)
    FLASH_COLOR = value(45, since=944)
    FLASH_ILLUMINANCE = value(46, since=944)
    AMBIENT_COLOR = value(47, since=944)
    AMBIENT_ILLUMINANCE = value(48, since=944)
    EMISSIVE_DESATURATION = value(49, since=975)
    SKY_INTENSITY = value(50, since=975)
    ORBITAL_OFFSET_DEGREES = value(51, since=975)


@packet(id=331, since=859)
class GraphicsOverrideParameterPacket:
    """Sent from the server to the client when a server script changes the rendering
    settings."""

    keyframes: dict[float, Vec3]
    float_value: float | None = field(since=924)
    vec3_value: Vec3 | None = field(since=924)
    biome_id: str
    parameter_id: GraphicsOverrideParameterType = field(type=uint8)
    reset_parameter: bool


@type(since=975)
class ScriptPrimitiveShapeType(IntEnum):
    LINE = 0
    BOX = 1
    SPHERE = 2
    CIRCLE = 3
    TEXT = 4
    ARROW = 5


@type(since=975)
class ArrowDataPayload:
    end_location: Vec3 | None
    arrow_head_length: float | None
    arrow_head_radius: float | None
    num_segments: uint8 | None


@type(since=975)
class TextDataPayload:
    text: str
    use_rotation: bool
    background_color: Color | None
    depth_test: bool
    show_backface: bool
    show_text_backface: bool


@type(since=975)
class BoxDataPayload:
    box_bound: Vec3


@type(since=975)
class LineDataPayload:
    end_location: Vec3


@type(since=975)
class SphereDataPayload:
    num_segments: uint8


@type(since=975)
class PrimitiveShapeDataPayload:
    network_id: uvarint64
    shape_type: ScriptPrimitiveShapeType | None = field(type=uint8)
    location: Vec3 | None
    scale: float | None
    rotation: Vec3 | None
    time_left_total_sec: float | None
    max_render_distance: float | None
    color: Color | None
    dimension_id: DimensionType | None
    attached_to_id: ActorUniqueID | None
    extra_data_payload: None | ArrowDataPayload | TextDataPayload | BoxDataPayload | LineDataPayload | SphereDataPayload


@packet(id=328, since=975)
class PrimitiveShapesPacket:
    shapes: list[PrimitiveShapeDataPayload]
