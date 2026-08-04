import uuid
from enum import IntEnum

from protocol import field, int8, packet, uint32, uint8
from protocol.common import Color

package = "bedrock.protocol"


class ArmSizeType(IntEnum, uint8):
    SLIM = 0
    WIDE = 1


class PieceType(IntEnum, uint32):
    SKELETON = 1
    BODY = 2
    SKIN = 3
    BOTTOM = 4
    FEET = 5
    DRESS = 6
    TOP = 7
    HIGH_PANTS = 8
    HANDS = 9
    OUTERWEAR = 10
    FACIAL_HAIR = 11
    MOUTH = 12
    EYES = 13
    HAIR = 14
    HOOD = 15
    BACK = 16
    FACE_ACCESSORY = 17
    HEAD = 18
    LEGS = 19
    LEFT_LEG = 20
    RIGHT_LEG = 21
    ARMS = 22
    LEFT_ARM = 23
    RIGHT_ARM = 24
    CAPES = 25
    CLASSIC_SKIN = 26
    EMOTE = 27


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


class SerializedPersonaPieceHandle:
    piece_id: str
    piece_type: PieceType = field(type=uint32)
    pack_id: uuid.UUID
    is_default_piece: bool
    product_id: str


class TintMapColor:
    colors: list[Color] = field(count=lambda t: 4)


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
