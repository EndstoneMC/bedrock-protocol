from enum import Enum, IntEnum

from protocol import field, int32, packet, uint8, uvarint32
from protocol.actor import ActorUniqueID
from protocol.common import Vec3

package = "bedrock.protocol"


class UpdateType(Enum, uint8):
    CLEAR_OVERRIDES = 0, "ClearOverrides"
    REMOVE_OVERRIDE = 1, "RemoveOverride"
    SET_INT_OVERRIDE = 2, "SetIntOverride"
    SET_FLOAT_OVERRIDE = 3, "SetFloatOverride"


@packet(id=325, until=2168)
class PlayerUpdateEntityOverridesPacket:
    id: ActorUniqueID
    property_index: uvarint32
    update_type: UpdateType
    int_value: int32 = field(when=lambda p: p.update_type == UpdateType.SET_INT_OVERRIDE)
    float_value: float = field(when=lambda p: p.update_type == UpdateType.SET_FLOAT_OVERRIDE)


@packet(id=325, since=2168)
class PlayerUpdateEntityOverridesPacket:
    # TODO: confirm against BDS -- the dump name-codes these; CloudburstMC
    # PlayerUpdateEntityOverridesSerializer_v2168 writes a single byte instead.
    class ClearOverride:
        update_type: UpdateType = field(type=str)

    class RemoveOverride:
        update_type: UpdateType = field(type=str)

    class IntOverride:
        update_type: UpdateType = field(type=str)
        value: int32

    class FloatOverride:
        update_type: UpdateType = field(type=str)
        value: float

    id: ActorUniqueID
    property_index: uvarint32
    update: ClearOverride | RemoveOverride | IntOverride | FloatOverride


@packet(id=326, until=2168)
class PlayerLocationPacket:
    class Type(IntEnum, int32):
        PLAYER_LOCATION_COORDINATES = 0
        PLAYER_LOCATION_HIDE = 1

    type: Type = field(type=int32)
    id: ActorUniqueID
    pos: Vec3 = field(when=lambda p: p.type == Type.PLAYER_LOCATION_COORDINATES)


@packet(id=326, since=2168)
class PlayerLocationPacket:
    class Type(IntEnum, int32):
        PLAYER_LOCATION_COORDINATES = 0
        PLAYER_LOCATION_HIDE = 1

    class CoordinatesLocation:
        type: Type
        pos: Vec3

    class HiddenLocation:
        type: Type

    id: ActorUniqueID
    location: CoordinatesLocation | HiddenLocation
