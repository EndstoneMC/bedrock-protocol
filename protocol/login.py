from protocol import field, packet, uint64, uvarint32

package = "bedrock.protocol"


@packet(id=135, until=1001)
class ClientCacheBlobStatusPacket:
    """Sent periodically by the client to update the server on which blobs it has
    (ACK) and which blobs it is lacking (MISS)."""

    missing_count: uvarint32
    found_count: uvarint32
    missing_ids: list[uint64] = field(count=lambda p: p.missing_count)
    found_ids: list[uint64] = field(count=lambda p: p.found_count)


@packet(id=135, since=1001)
class ClientCacheBlobStatusPacket:
    """Sent periodically by the client to update the server on which blobs it has
    (ACK) and which blobs it is lacking (MISS)."""

    missing_ids: list[uint64]
    found_ids: list[uint64]
