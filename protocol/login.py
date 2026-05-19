from enum import IntEnum

from protocol._dsl import field, packet, value
from protocol.common import int32, uint32

package = "bedrock.protocol"


@packet(id=1)
class LoginPacket:
    """Sent once from client to server at login. About 100k."""

    client_network_version: int32 = field(endian="big")
    connection_request: str


class PlayStatus(IntEnum):
    LOGIN_SUCCESS = 0
    LOGIN_FAILED_CLIENT_OLD = 1
    LOGIN_FAILED_SERVER_OLD = 2
    PLAYER_SPAWN = 3
    LOGIN_FAILED_INVALID_TENANT = 4
    LOGIN_FAILED_EDITION_MISMATCH_EDU_TO_VANILLA = 5
    LOGIN_FAILED_EDITION_MISMATCH_VANILLA_TO_EDU = 6
    LOGIN_FAILED_SERVER_FULL_SUB_CLIENT = 7
    LOGIN_FAILED_EDITOR_MISMATCH_EDITOR_TO_VANILLA = value(8, since=534)
    LOGIN_FAILED_EDITOR_MISMATCH_VANILLA_TO_EDITOR = value(9, since=534)


@packet(id=2)
class PlayStatusPacket:
    """Describes the login status of the player."""

    status: PlayStatus = field(type=uint32, endian="big")


@packet(id=94)
class SubClientLoginPacket:
    connection_request: str
