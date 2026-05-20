from enum import IntEnum

from protocol import field, int32, packet, type, uint8, uint16

package = "bedrock.protocol"


@type(since=554)
class PacketCompressionAlgorithm(IntEnum):
    ZLIB = 0
    SNAPPY = 1
    NONE = 0xFFFF


@packet(id=143)
class NetworkSettingsPacket:
    """Sends tunable options from host to client (compression threshold and
    algorithm)."""

    compression_threshold: uint16
    compression_algorithm: PacketCompressionAlgorithm = field(type=uint16, since=554)
    client_throttle_enabled: bool = field(since=554)
    client_throttle_threshold: uint8 = field(since=554)
    client_throttle_scalar: float = field(since=554)


@packet(id=193)
class RequestNetworkSettingsPacket:
    """Requests tunable options from host to client (compression threshold and
    algorithm). This is the initial packet sent from the client to initiate a
    connection. NOTE: this packet should not contain anything other than the
    client version, don't add new data here."""

    client_network_version: int32 = field(endian="big")
