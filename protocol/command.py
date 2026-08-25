from enum import IntEnum

from protocol import packet, uint8, value

package = "bedrock.protocol"


class CommandPermissionLevel(IntEnum, uint8):
    ANY = 0
    GAME_DIRECTORS = value(1, "GameDirectors")
    ADMIN = 2
    HOST = 3
    OWNER = 4
    INTERNAL = 5


@packet(id=140, since=2168)
class SettingsCommandPacket:
    command_string: str
    suppress_output: bool
