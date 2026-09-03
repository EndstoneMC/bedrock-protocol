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
    HIGHLIGHTS_GAIN = 26
    HIGHLIGHTS_GAMMA = 27
    HIGHLIGHTS_OFFSET = 28
    HIGHLIGHTS_SATURATION = 29
    MIDTONES_GAIN = 30
    MIDTONES_GAMMA = 31
    MIDTONES_OFFSET = 32
    MIDTONES_SATURATION = 33
    SHADOWS_GAIN = 34
    SHADOWS_GAMMA = 35
    SHADOWS_OFFSET = 36
    SHADOWS_SATURATION = 37
    HIGHLIGHTS_MIN = 38
    SHADOWS_MAX = 39
    TEMPERATURE = 40
    SUN_COLOR = 41
    SUN_ILLUMINANCE = 42
    MOON_COLOR = 43
    MOON_ILLUMINANCE = 44
    FLASH_COLOR = 45
    FLASH_ILLUMINANCE = 46
    AMBIENT_COLOR = 47
    AMBIENT_ILLUMINANCE = 48
    EMISSIVE_DESATURATION = 49
    SKY_INTENSITY = 50
    ORBITAL_OFFSET_DEGREES = 51


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
