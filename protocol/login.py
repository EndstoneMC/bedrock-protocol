from enum import IntEnum

from protocol import field, int32, packet, uint32, uint64, uvarint32, value
from protocol.actor import ActorRuntimeID

package = "bedrock.protocol"


@packet(id=135, since=361, until=1001)
class ClientCacheBlobStatusPacket:
    """Client Cache Blob Status Packet. Sent periodically by the client to
    update the server on which blob it has (ACK) and which blobs it is lacking
    (MISS)."""

    missing_count: uvarint32
    found_count: uvarint32
    missing_ids: list[uint64] = field(count=lambda p: p.missing_count)
    found_ids: list[uint64] = field(count=lambda p: p.found_count)


# v1001 (cereal migration): the leading missing/found counts gave way to two
# ordinary uvarint32-prefixed lists, so each count now immediately precedes its
# own elements instead of both counts being written up front.
@packet(id=135, since=1001)
class ClientCacheBlobStatusPacket:
    """Client Cache Blob Status Packet. Sent periodically by the client to
    update the server on which blob it has (ACK) and which blobs it is lacking
    (MISS)."""

    missing_ids: list[uint64]
    found_ids: list[uint64]


class MissingBlobData:
    blob_id: uint64  # ClientBlobCache::BlobId == uint64_t
    blob_data: bytes


@packet(id=136, since=361)
class ClientCacheMissResponsePacket:
    """Only active in a real client-server scenario. This packet is just a list
    of <blobId, blob> pairs sent from server to client."""

    blobs: list[MissingBlobData]


@packet(id=129, since=361)
class ClientCacheStatusPacket:
    """It is sent by the Client once, at login, to communicate if it supports
    the cache or not."""

    enabled: bool


@packet(id=4)
class ClientToServerHandshakePacket:
    """Sets up encryption and authenticates in educational version once at level
    startup from client."""

    pass


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


@packet(id=3)
class ServerToClientHandshakePacket:
    """Sent from the server at the end of the login packet."""

    data: str


@packet(id=113)
class SetLocalPlayerAsInitializedPacket:
    """Client tells the server that the client is ready to roll."""

    player_id: ActorRuntimeID


@packet(id=94)
class SubClientLoginPacket:
    connection_request: str
