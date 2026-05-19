from enum import IntEnum

from protocol._dsl import field, packet, type
from protocol.common import int32, uint8, uint16

package = "bedrock.protocol"


@type(since=554)
class PacketCompressionAlgorithm(IntEnum):
    ZLIB = 0
    SNAPPY = 1
    NONE = 0xFFFF


@packet(id=143)
class NetworkSettingsPacket:
    """Server reply to RequestNetworkSettingsPacket that sets up
    compression and client-side packet throttling."""

    compression_threshold: uint16
    compression_algorithm: PacketCompressionAlgorithm = field(type=uint16, since=554)
    client_throttle_enabled: bool = field(since=554)
    client_throttle_threshold: uint8 = field(since=554)
    client_throttle_scalar: float = field(since=554)


@packet(id=193)
class RequestNetworkSettingsPacket:
    """This is the initial packet sent from the client to initiate a connection.

    NOTE: this packet should not contain anything other than the client version.
    """

    client_network_version: int32 = field(endian="big")
