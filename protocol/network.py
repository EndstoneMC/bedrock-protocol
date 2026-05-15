from enum import IntEnum

from protocol._dsl import field, packet
from protocol.common import int32, uint16, uint8

package = "bedrock.protocol"


class PacketCompressionAlgorithm(IntEnum):
    Z_LIB = 0
    SNAPPY = 1
    NONE = 0xFFFF


@packet(id=143)
class NetworkSettingsPacket:
    """Server reply to RequestNetworkSettingsPacket that sets up
    compression and client-side packet throttling."""

    compression_threshold: uint16
    compression_algorithm: PacketCompressionAlgorithm = field(type=uint16)
    client_throttle_enabled: bool
    client_throttle_threshold: uint8
    client_throttle_scalar: float


@packet(id=193)
class RequestNetworkSettingsPacket:
    """This is the initial packet sent from the client to initiate a connection.

    NOTE: this packet should not contain anything other than the client version.
    """

    client_network_version: int32 = field(endian="big")
