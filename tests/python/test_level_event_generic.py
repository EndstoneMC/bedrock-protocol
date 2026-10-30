import gc

import pytest
from conftest import varuint

import bedrock_protocol as bp
from bedrock_protocol.wire import BatchCodec

CAPTURED = bytes.fromhex(
    "7c929901030b61626c65546f536c6565700203146f766572776f726c64506c61796572436f756e74"
    "020313736c656570696e67506c61796572436f756e740000"
)


def test_captured_payload_and_owned_public_members():
    codec = bp.Codec(2193)
    decoded = codec.decode_packet(CAPTURED)
    packet = decoded.payload
    assert type(packet) is bp.v2193.LevelEventGenericPacket
    assert decoded.header.packet_id == 124
    assert packet.event_id == 9801
    assert len(CAPTURED[1:]) == 63
    assert len(packet.data) == 3
    assert packet.wire_bytes() == CAPTURED[1:]
    assert codec.encode_packet(packet) == CAPTURED
    fields = {"ableToSleep": 1, "overworldPlayerCount": 1, "sleepingPlayerCount": 0}
    for name, value in fields.items():
        assert packet.data[name].type == bp.NbtType.INT
        assert packet.data[name].value == value
    rebuilt = bp.v2193.LevelEventGenericPacket(event_id=9801, data=packet.data)
    retained = packet.data
    del decoded, packet, codec
    gc.collect()
    assert retained["ableToSleep"].value == 1
    assert bp.Codec(2193).encode_packet(rebuilt) == CAPTURED


@pytest.mark.parametrize("version", [v for v in bp.SUPPORTED_VERSIONS if v != 2193])
@pytest.mark.parametrize("fixture", ["golden", "golden_empty_tag"])
def test_other_eighteen_versions_keep_complete_root(version, fixture, golden):
    codec = bp.Codec(version)
    data = golden(124, "test_124_level_event_generic.cpp", fixture)
    packet = codec.decode_packet(data).payload
    assert type(packet) is getattr(bp, f"v{version}").LevelEventGenericPacket
    assert codec.encode_packet(packet) == data
    assert packet.wire_bytes() == data[1:]


def test_snapshot_identity_and_supported_version_boundary():
    assert bp.v2193.LevelEventGenericPacket is not bp.v2168.LevelEventGenericPacket
    assert bp.v2193.LevelEventGenericPacket is not bp.v2225.LevelEventGenericPacket
    assert max(bp.SUPPORTED_VERSIONS) == 2225
    with pytest.raises(bp.UnsupportedVersionError):
        bp.Codec(2194)


@pytest.mark.parametrize("invalid", [CAPTURED[:-1], CAPTURED + b"\x00"])
def test_incomplete_and_trailing_payload_reject_and_recover(invalid):
    with pytest.raises(bp.DecodeError):
        bp.Codec(2193).decode_packet(invalid)
    batch = BatchCodec(bp.Codec(2193))
    with pytest.raises(bp.DecodeError):
        batch.decode(varuint(len(invalid)) + invalid)
    with pytest.raises(RuntimeError, match="terminal"):
        batch.decode(varuint(len(CAPTURED)) + CAPTURED)
    recovered = BatchCodec(bp.Codec(2193)).decode(
        varuint(len(invalid)) + invalid + varuint(len(CAPTURED)) + CAPTURED,
        recover_packet_errors=True,
    )
    assert len(recovered.errors) == 1
    assert recovered.errors[0].header.packet_id == 124
    assert len(recovered) == 1 and recovered[0].payload.event_id == 9801


@pytest.mark.parametrize(
    "limits",
    [
        bp.DecodeLimits(max_depth=2),
        bp.DecodeLimits(max_decoded_bytes=0),
        bp.DecodeLimits(max_decoded_elements=0),
    ],
)
def test_payload_resource_failures_stay_fatal(limits):
    batch = BatchCodec(bp.Codec(2193, limits=limits))
    with pytest.raises(bp.DecodeError):
        batch.decode(varuint(len(CAPTURED)) + CAPTURED, recover_packet_errors=True)
    with pytest.raises(RuntimeError, match="terminal"):
        batch.decode(varuint(len(CAPTURED)) + CAPTURED, recover_packet_errors=True)
