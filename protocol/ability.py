from enum import IntEnum

from protocol import field, int64, packet, uint16, varint32
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
