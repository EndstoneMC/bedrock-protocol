from enum import IntEnum

from protocol import field, int32, int64, packet, type, uint8, uint16, varint32

package = "bedrock.protocol"


@type(since=554)
class PacketCompressionAlgorithm(IntEnum):
    ZLIB = 0
    SNAPPY = 1
    NONE = 0xFFFF


@packet(id=143, since=388)
class NetworkSettingsPacket:
    """Sends tunable options from host to client (compression threshold and
    algorithm)."""

    compression_threshold: uint16
    compression_algorithm: PacketCompressionAlgorithm = field(type=uint16, since=554)
    client_throttle_enabled: bool = field(since=554)
    client_throttle_threshold: uint8 = field(since=554)
    client_throttle_scalar: float = field(since=554)


@packet(id=115)
class NetworkStackLatencyPacket:
    """Ping packet used to provide ping time to in-game debug graph, also for
    realms telemetry of actual in-game latency. Sent from both client and
    server."""

    create_time: int64
    from_server: bool = field(since=332)


@type(since=407)
class PacketViolationType(IntEnum):
    UNKNOWN = -1
    PACKET_MALFORMED = 0


@type(since=407)
class PacketViolationSeverity(IntEnum):
    UNKNOWN = -1
    WARNING = 0
    FINAL_WARNING = 1
    TERMINATING_CONNECTION = 2


@packet(id=156, since=407)
class PacketViolationWarningPacket:
    """This is sent when the client detects a malformed packet."""

    violation_type: PacketViolationType = field(type=varint32)
    violation_severity: PacketViolationSeverity = field(type=varint32)
    violating_packet_id: varint32
    violation_context: str


@packet(id=193, since=554)
class RequestNetworkSettingsPacket:
    """Requests tunable options from host to client (compression threshold and
    algorithm). This is the initial packet sent from the client to initiate a
    connection. NOTE: this packet should not contain anything other than the
    client version, don't add new data here."""

    client_network_version: int32 = field(endian="big")
