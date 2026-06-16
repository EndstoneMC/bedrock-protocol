from enum import IntEnum

from protocol import (
    field,
    int32,
    packet,
    type,
    uint8,
    uint32,
    uint64,
    uvarint32,
    uvarint64,
    value,
    varint32,
)
from protocol.actor import ActorUniqueID
from protocol.common import Color, Vec2, Vec3
from protocol.dimension import DimensionType

package = "bedrock.protocol"


@type(since=428)
class DebugMarkerData:
    text: str
    position: Vec3
    color_red: float
    color_green: float
    color_blue: float
    color_alpha: float
    duration_ms: uint64


@packet(id=164, since=428)
class ClientboundDebugRendererPacket:
    """Used to add/remove debug rendering objects."""

    class PayloadType(IntEnum):
        INVALID = 0
        CLEAR_DEBUG_MARKERS = 1
        ADD_DEBUG_MARKER_CUBE = 2

    # TODO: three references give three distinct shapes for payload_type:
    # CloudburstMC writes a uvarint32 ordinal in [428, 671) and int32-LE
    # ordinal in [671, latest]; EndstoneMC protocol-docs and gophertunnel
    # both say it is a length-prefixed string ("cleardebugmarkers" /
    # "adddebugmarkercube") instead. Modeled here as the v671+ int32-LE
    # form because the BDS PayloadType : uint8_t header most directly
    # matches a numeric ordinal, but the pre-v671 uvarint32 era and the
    # protocol-docs string form both still need a separate codec path.
    payload_type: PayloadType = field(type=int32)
    debug_marker_data: DebugMarkerData = field(
        when=lambda p: p.payload_type == PayloadType.ADD_DEBUG_MARKER_CUBE,
    )


@packet(id=336, since=924)
class ClientboundTextureShiftPacket:
    """Sends a set of update properties for the texture shift system from the server to the client."""

    class Action(IntEnum):
        INVALID = 0
        INITIALIZE = 1
        START = 2
        SET_ENABLED = 3
        SYNC = 4

    action: Action = field(type=uint8)
    collection_name: str
    from_step: str
    to_step: str
    all_steps: list[str]
    current_length_in_ticks: uvarint64
    total_length_in_ticks: uvarint64
    enabled: bool


@type(since=975)
class ScriptPrimitiveShapeType(IntEnum):
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


@type(since=975)
class ArrowDataPayload:
    end_location: Vec3 | None
    arrow_head_length: float | None
    arrow_head_radius: float | None
    num_segments: uint8 | None


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
class CircleDataPayload:
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


@type(since=975)
class TextDataPayload:
    text: str
    use_rotation: bool
    background_color: Color | None
    depth_test: bool
    show_backface: bool
    show_text_backface: bool


@type(since=975)
class PrimitiveShapeDataPayload:
    """Wire shape mirrors ScriptModuleMinecraft::ScriptPrimitiveShape::populatePacketData. Most
    fields are gated by per-instance dirty flags on the server, so they ride as optionals."""

    network_id: uvarint64
    shape_type: ScriptPrimitiveShapeType | None = field(type=uint8)
    location: Vec3 | None
    scale: float | None
    rotation: Vec3 | None
    time_left_total_sec: float | None
    # COMPILER_EXTENSION_NEEDED: max_render_distance (mMaxRenderDistance) was inserted
    # before color in the v975 codec but the BDS payload struct still lists it last. The DSL
    # has no `since` interleaving inside a single struct declaration that reorders fields, so
    # the v975 insertion point needs codegen support.
    max_render_distance: float | None
    color: Color | None
    dimension_id: int | None = field(type=varint32, since=859, until=924)
    dimension_id: DimensionType | None = field(since=924)
    attached_to_id: ActorUniqueID | None = field(since=924)
    # Pre-v859, the variant payload was inlined as a fixed sequence of optionals per shape kind
    # rather than tag-discriminated. The since=859 codec switches to writing a uvarint payload
    # type ahead of the variant body. v1001 grew the discriminant with cylinder, pyramid,
    # ellipsoid, and cone shape payloads.
    extra_data_payload: (
        None
        | ArrowDataPayload
        | TextDataPayload
        | BoxDataPayload
        | LineDataPayload
        | SphereDataPayload
        | CircleDataPayload
    ) = field(tag=uint8, since=859, until=1001)
    extra_data_payload: (
        None
        | ArrowDataPayload
        | TextDataPayload
        | BoxDataPayload
        | LineDataPayload
        | SphereDataPayload
        | CircleDataPayload
        | CylinderDataPayload
        | PyramidDataPayload
        | EllipsoidDataPayload
        | ConeDataPayload
    ) = field(tag=uint8, since=1001)


@packet(id=328, since=975)
class PrimitiveShapesPacket:
    """Send primitive drawing shape info (from scripting) to the client for rendering."""

    shapes: list[PrimitiveShapeDataPayload]


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
    """Sent from the server to the client when a server script changes the rendering settings."""

    keyframes: list[tuple[float, Vec3]]
    float_value: float | None = field(since=924)
    vec3_value: Vec3 | None = field(since=924)
    biome_id: str
    player_identifier: str | None = field(since=1001)
    parameter_id: GraphicsOverrideParameterType = field(type=uint8)
    reset_parameter: bool


@packet(id=130, since=354)
class OnScreenTextureAnimationPacket:
    """Sent from the player (and in one case from the village) to make those really cool animated effects for the hero of the village and the totem saving you."""

    effect_id: uint32


@packet(id=160, since=419)
class PlayerFogPacket:
    """This is the packet that tracks the active fog stack from the server so the local players can apply different fog settings."""

    fog_stack: list[str]


@type(since=649)
class HudVisibility(IntEnum):
    HIDE = 0
    RESET = 1


@type(since=649)
class HudElement(IntEnum):
    PAPER_DOLL = 0
    ARMOR = 1
    TOOL_TIPS = 2
    TOUCH_CONTROLS = 3
    CROSSHAIR = 4
    HOT_BAR = 5
    HEALTH = 6
    PROGRESS_BAR = 7
    HUNGER = 8
    AIR_BUBBLES = 9
    HORSE_HEALTH = 10
    STATUS_EFFECTS = value(11, since=671)
    ITEM_TEXT = value(12, since=671)


@packet(id=308, since=649)
class SetHudPacket:
    """This packet is only used via the set hud command. This is for 3rd party content. This packet will toggle the HUD visibility."""

    # COMPILER_EXTENSION_NEEDED: each element is a HudElement enum, but list[Enum] cannot carry a `field(type=<primitive>)` override; the wire encoding switches from uvarint32 (<v786) to varint32 (>=v786)
    elements: list[uvarint32] = field(until=786)
    elements: list[varint32] = field(since=786)
    visibility: HudVisibility = field(type=uint8, until=786)
    visibility: HudVisibility = field(type=varint32, since=786)


@packet(id=88)
class SetTitlePacket:
    """Used by 3rd party content for the purpose of showing ui banners."""

    class TitleType(IntEnum):
        CLEAR = 0
        RESET = 1
        TITLE = 2
        SUBTITLE = 3
        ACTIONBAR = 4
        TIMES = 5
        TITLE_TEXT_OBJECT = 6
        SUBTITLE_TEXT_OBJECT = 7
        ACTIONBAR_TEXT_OBJECT = 8

    type: TitleType = field(type=varint32)
    title_text: str
    fade_in_time: varint32
    stay_time: varint32
    fade_out_time: varint32
    xuid: str = field(since=448)
    platform_online_id: str = field(since=448)
    filtered_title_text: str = field(since=712)


@packet(id=118, since=313)
class SpawnParticleEffectPacket:
    """This is not used for much anymore, only the Particle command (spawn
    particle by name at a location) and for ScriptServerSpawnParticleAttachedToActor
    and ScriptServerSpawnParticleInWorldEvent."""

    vanilla_dimension_id: uint8
    actor_id: ActorUniqueID = field(since=332)
    pos: Vec3
    effect_name: str
    molang_variables: str | None = field(since=503)


# bedrock-headers android/r26_u2 declares this id as VideoStreamConnect_DEPRECATED in
# MinecraftPacketIds. Neither CloudburstMC, gophertunnel, nor EndstoneMC/protocol-docs
# carries a body for it -- the id is allocated but the packet is no longer serialized.
# Empty stub kept so the id is not silently absent from the v975 enum surface.
@packet(id=125)
class VideoStreamConnectPacket:
    pass
