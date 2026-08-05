import uuid
from enum import Enum, IntEnum

from protocol import field, int8, packet, type, uint8, uint32
from protocol.common import Color

package = "bedrock.protocol"


class ArmSizeType(IntEnum, uint8):
    SLIM = 0
    WIDE = 1


class PieceType(Enum, uint32):
    SKELETON = 1, "Skeleton"
    BODY = 2, "Body"
    SKIN = 3, "Skin"
    BOTTOM = 4, "Bottom"
    FEET = 5, "Feet"
    DRESS = 6, "Dress"
    TOP = 7, "Top"
    HIGH_PANTS = 8, "High_Pants"
    HANDS = 9, "Hands"
    OUTERWEAR = 10, "Outerwear"
    FACIAL_HAIR = 11, "FacialHair"
    MOUTH = 12, "Mouth"
    EYES = 13, "Eyes"
    HAIR = 14, "Hair"
    HOOD = 15, "Hood"
    BACK = 16, "Back"
    FACE_ACCESSORY = 17, "FaceAccessory"
    HEAD = 18, "Head"
    LEGS = 19, "Legs"
    LEFT_LEG = 20, "LeftLeg"
    RIGHT_LEG = 21, "RightLeg"
    ARMS = 22, "Arms"
    LEFT_ARM = 23, "LeftArm"
    RIGHT_ARM = 24, "RightArm"
    CAPES = 25, "Capes"
    CLASSIC_SKIN = 26, "ClassicSkin"
    EMOTE = 27, "Emote"


class AnimatedTextureType(IntEnum, uint32):
    FACE = 1
    BODY_32X32 = 2
    BODY_128X128 = 3


class AnimationExpression(IntEnum, uint32):
    LINEAR = 0
    BLINKING = 1


class TrustedSkinFlag(IntEnum, int8):
    UNSET = 0
    FALSE = 1
    TRUE = 2


class SkinImage:
    width: uint32
    height: uint32
    image_bytes: bytes


class AnimatedImageData:
    image: SkinImage
    type: AnimatedTextureType
    frames: float
    animation_expression: AnimationExpression


@type(cereal=False)
class AnimatedImageData:
    """SerializedSkinImpl::write writes the image inline rather than through a
    SkinImage, and both enums uncompressed."""

    image_width: uint32
    image_height: uint32
    image_bytes: bytes
    type: AnimatedTextureType = field(type=uint32)
    frames: float
    animation_expression: AnimationExpression = field(type=uint32)


class SerializedPersonaPieceHandle:
    piece_id: str
    piece_type: PieceType = field(type=uint32)
    pack_id: uuid.UUID
    is_default_piece: bool
    product_id: str


# TODO: confirm against BDS -- the pre-cereal write name-codes the piece type through
# persona::stringFromPieceType(type, false), where cereal writes the enumerator verbatim.
# gophertunnel documents the former as `persona_skeleton`, `persona_body` and so on, which
# is not the `Skeleton` / `Body` this enum pairs for the cerealised call site. If the two
# really differ, one enum needs two name codings and this pairing is wrong here. No golden
# reaches it yet: a classic skin carries no persona pieces.
@type(cereal=False)
class SerializedPersonaPieceHandle:
    piece_id: str
    piece_type: PieceType = field(type=str)
    pack_id: str
    is_default_piece: bool
    product_id: str


class TintMapColor:
    colors: list[Color] = field(count=lambda t: 4)


@type(cereal=False)
class TintMapColor:
    """The pre-cereal write walks the map as a list, so each entry carries its own
    key and the colours their own count."""

    piece_type: PieceType = field(type=str)
    colors: list[str] = field(prefix=uint32)


@type(cereal=False)
class SerializedSkinRef:
    """SerializedSkinImpl::write. The arm size and skin colour go as strings
    rather than as an enumerator and a packed colour, each list takes a fixed
    count, and the trusted flag is absent -- PlayerListPacket writes it as a
    trailing run of its own, one bool per entry."""

    id: str
    play_fab_id: str
    resource_patch: str
    image_width: uint32
    image_height: uint32
    image_bytes: bytes
    animated_image_data: list[AnimatedImageData] = field(cereal=False, prefix=uint32)
    cape_image_width: uint32
    cape_image_height: uint32
    cape_image_bytes: bytes
    geometry_data: str
    geometry_data_min_engine_version: str
    animation_data: str
    cape_id: str
    full_id: str
    arm_size: ArmSizeType = field(type=str)
    skin_color: str
    persona_pieces: list[SerializedPersonaPieceHandle] = field(cereal=False, prefix=uint32)
    piece_tint_colors: list[TintMapColor] = field(cereal=False, prefix=uint32)
    is_premium: bool
    is_persona: bool
    is_persona_cape_on_classic_skin: bool
    is_primary_user: bool
    overrides_player_appearance: bool


class SerializedSkinRef:
    id: str
    play_fab_id: str
    resource_patch: str
    image_data: SkinImage
    animated_image_data: list[AnimatedImageData]
    cape_image_data: SkinImage
    geometry_data: str
    geometry_data_min_engine_version: str
    animation_data: str
    cape_id: str
    full_id: str
    arm_size: ArmSizeType
    skin_color: Color
    persona_pieces: list[SerializedPersonaPieceHandle]
    piece_tint_colors: dict[PieceType, TintMapColor] = field(type=str)
    is_premium: bool
    is_persona: bool
    is_persona_cape_on_classic_skin: bool
    is_primary_user: bool
    overrides_player_appearance: bool
    trusted_skin_flag: TrustedSkinFlag = field(type=str)
    profile_hash: str = field(since=2168)


# TODO: confirm against BDS -- CloudburstMC PlayerSkinSerializer_v390 appends a
# trailing bool isTrustedSkin here and its v2168 override drops it again; neither
# dump has that field, and both carry TrustedSkinFlag inside the skin instead.
@packet(id=93)
class PlayerSkinPacket:
    uuid: uuid.UUID
    skin: SerializedSkinRef
    localized_new_skin_name: str
    localized_old_skin_name: str
