"""Server-driven rendering-parameter overrides."""

from enum import IntEnum

from protocol import field, packet, uint8, value
from protocol.common import Vec3

package = "bedrock.protocol"


class GraphicsOverrideParameterType(IntEnum, uint8):
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
    CDOM = value(11, cpp_name="CDOM")
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


@packet(id=331)
class GraphicsOverrideParameterPacket:
    """Sent from the server to the client when a server script changes the rendering settings."""

    keyframes: dict[float, Vec3]
    float_value: float | None
    vec3_value: Vec3 | None
    biome_id: str
    player_id: str | None = field(since=1001)
    parameter_id: GraphicsOverrideParameterType
    reset_parameter: bool
