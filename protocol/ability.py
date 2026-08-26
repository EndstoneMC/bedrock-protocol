from enum import IntEnum, auto

from protocol import field, int8, int64, packet, uint8, uint16, varint32
from protocol.actor import ActorUniqueID
from protocol.camera import Scheme
from protocol.game import PlayerPermissionLevel

package = "bedrock.protocol"


@packet(id=185, since=2168)
class RequestPermissionsPacket:
    class CustomPermissions(IntEnum, uint16):
        BUILD = 1
        MINE = 2
        DOORS_AND_SWITCHES = 4
        OPEN_CONTAINERS = 8
        ATTACK_PLAYERS = 16
        ATTACK_MOBS = 32
        OPERATOR_COMMANDS = 64
        TELEPORT = 128

    target_player_id: ActorUniqueID = field(type=int64)
    player_permissions: PlayerPermissionLevel = field(type=varint32)
    custom_permission_flags: uint16


@packet(id=327, since=2168)
class ClientboundControlSchemeSetPacket:
    control_scheme: Scheme


class AdventureSettings:
    no_pv_m: bool
    no_mv_p: bool
    immutable_world: bool
    show_name_tags: bool
    auto_jump: bool


@packet(id=188, since=2168)
class UpdateAdventureSettingsPacket:
    adventure_settings: AdventureSettings


class AbilitiesIndex(IntEnum, int8):
    INVALID = -1
    BUILD = 0
    MINE = 1
    DOORS_AND_SWITCHES = 2
    OPEN_CONTAINERS = 3
    ATTACK_PLAYERS = 4
    ATTACK_MOBS = 5
    OPERATOR_COMMANDS = 6
    TELEPORT = 7
    INVULNERABLE = 8
    FLYING = 9
    MAY_FLY = 10
    INSTABUILD = 11
    LIGHTNING = 12
    FLY_SPEED = 13
    WALK_SPEED = 14
    MUTED = 15
    WORLD_BUILDER = 16
    NO_CLIP = 17
    PRIVILEGED_BUILDER = 18
    VERTICAL_FLY_SPEED = 19
    ABILITY_COUNT = auto()


@packet(id=184, since=2168)
class RequestAbilityPacket:
    class Type(IntEnum, uint8):
        UNSET = 0
        BOOL = 1
        FLOAT = 2

    ability: AbilitiesIndex = field(type=varint32)
    value_type: Type
    bool_: bool
    float_: float
