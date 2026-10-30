import gc
import subprocess
import sys
import zlib
from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import varuint

import bedrock_protocol as bp
from bedrock_protocol.wire import BatchCodec, Compression


def frame(*packets):
    return b"".join(varuint(len(packet)) + packet for packet in packets)


def test_no_transport_prefix_and_independent_deflate(golden):
    codec = bp.Codec(2193)
    data = golden(2, "test_002_play_status.cpp")
    packet = codec.decode_packet(data).payload
    expected = frame(data)
    batch = BatchCodec(codec)
    assert batch.encode([packet]) == expected
    batch.set_compression(Compression.ZLIB, 0)
    compressor = zlib.compressobj(wbits=-15)
    compressed = b"\x00" + compressor.compress(expected) + compressor.flush()
    assert batch.encode([packet]) == compressed
    decoded = batch.decode(compressed)
    assert len(decoded) == decoded.packet_count == decoded.decoded_count == 1
    assert not decoded.filtered
    assert decoded.skipped_packet_ids == ()
    assert decoded.errors == ()
    assert decoded[0].payload.status == bp.v2193.PlayStatus.PLAYER_SPAWN


@pytest.mark.parametrize(
    "algorithm,wire",
    [
        (Compression.ZLIB, "00636664620600"),
        (Compression.SNAPPY, "01040c03010203"),
        (Compression.NONE, "ff03010203"),
    ],
)
def test_existing_independent_batch_vectors(algorithm, wire):
    # bedrock-bot/tests/test_batch.cpp; only its transport marker is removed.
    batch = BatchCodec(bp.Codec(2193))
    batch.set_compression(algorithm, 0)
    result = batch.decode(bytes.fromhex(wire), packet_ids=[])
    assert result.filtered
    assert result.packet_count == 1 and result.decoded_count == 0
    assert result.headers[0].packet_id == 1
    assert result.skipped_packet_ids == (1,)


@pytest.mark.parametrize("algorithm", [Compression.ZLIB, Compression.SNAPPY, Compression.NONE])
def test_threshold_and_uncompressed_escape(algorithm, golden):
    codec = bp.Codec(2193)
    packet = codec.decode_packet(golden(2, "test_002_play_status.cpp")).payload
    prepared = codec.prepare_packet(packet)
    plaintext = frame(codec.encode_packet(packet))
    batch = BatchCodec(codec)
    assert batch.encode_prepared([prepared]) == batch.encode([packet]) == plaintext
    for threshold in (len(plaintext) + 1, len(plaintext), 0):
        batch.set_compression(algorithm, threshold)
        wire = batch.encode([packet])
        assert batch.encode_prepared([prepared]) == wire
        assert (wire[0] == 255) == (algorithm == Compression.NONE or threshold > len(plaintext))
        for encoded in (wire, b"\xff" + plaintext):
            assert [decoded.payload.status for decoded in batch.decode(encoded)] == [packet.status]


def test_batch_failure_is_terminal_and_never_publishes_prefix(golden):
    codec = bp.Codec(2193)
    good = golden(2, "test_002_play_status.cpp")
    packet = codec.decode_packet(good).payload
    for invalid in [
        frame(good, varuint(2) + b"\x00"),
        frame(good) + b"\x80",
        frame(good, varuint(1 << 14)),
        bytes.fromhex("ffffffff10"),
        b"",
        frame(varuint(9)),
    ]:
        batch = BatchCodec(codec)
        with pytest.raises(bp.DecodeError):
            batch.decode(invalid)
        with pytest.raises(RuntimeError, match="terminal"):
            batch.decode(frame(good))
        with pytest.raises(RuntimeError, match="terminal"):
            batch.encode([packet])
        with pytest.raises(RuntimeError, match="terminal"):
            batch.set_compression(Compression.NONE, 0)
        with pytest.raises(RuntimeError, match="terminal"):
            batch.enable_encryption(bytes(32))


def test_filter_is_explicit_and_validates_every_header(golden):
    good = golden(2, "test_002_play_status.cpp")
    unknown = varuint(1023) + b"opaque"
    data = frame(varuint(9), good, unknown)
    batch = BatchCodec(bp.Codec(2193))
    result = batch.decode(data, packet_ids={2, 1023})
    assert result.filtered and result.skipped_packet_ids == (9,)
    assert [header.packet_id for header in result.headers] == [9, 2, 1023]
    assert [packet.header.packet_id for packet in result] == [2, 1023]
    with pytest.raises(bp.DecodeError):
        batch.decode(frame(good, varuint(1 << 14)), packet_ids={2})


def test_aggregate_decoding_budget(golden):
    data = golden(136, "test_136_client_cache_miss_response.cpp")
    limits = bp.DecodeLimits(max_decoded_elements=3)
    assert len(bp.Codec(2193, limits=limits).decode_packet(data).payload.blobs) == 2
    batch = BatchCodec(bp.Codec(2193, limits=limits))
    with pytest.raises(bp.DecodeError):
        batch.decode(frame(data, data))
    skipped = BatchCodec(bp.Codec(2193, limits=bp.DecodeLimits(max_decoded_elements=0)))
    assert skipped.decode(frame(data, data), packet_ids=set()).skipped_packet_ids == (136, 136)


def test_batch_iterator_and_payload_own_storage(golden):
    batch = BatchCodec(bp.Codec(2193))
    result = batch.decode(frame(golden(136, "test_136_client_cache_miss_response.cpp")))
    iterator = iter(result)
    del result, batch
    gc.collect()
    packet = next(iterator)
    assert packet.payload.blobs[0].blob_data.to_bytes() == b"chunk"
    with pytest.raises(StopIteration):
        next(iterator)


def test_owner_thread_and_reentrant_access(golden):
    codec = bp.Codec(2193)
    batch = BatchCodec(codec)
    data = golden(2, "test_002_play_status.cpp")
    with ThreadPoolExecutor(max_workers=1) as pool:
        for action in [
            lambda: batch.decode(frame(data)),
            lambda: batch.set_compression(Compression.NONE, 0),
            lambda: batch.enable_encryption(bytes(32)),
            lambda: batch.encode([]),
        ]:
            with pytest.raises(RuntimeError, match="owner thread"):
                pool.submit(action).result()

    class Packets:
        def __iter__(self):
            batch.set_compression(Compression.NONE, 0)
            yield codec.decode_packet(data).payload

    with pytest.raises(RuntimeError, match="reentrant"):
        batch.encode(Packets())
    assert len(batch.decode(frame(data))) == 1


@pytest.mark.parametrize("recover", [False, True])
def test_encrypted_order_checksum_and_argument_failure(golden, recover):
    codec = bp.Codec(2193)
    sender, receiver = BatchCodec(codec), BatchCodec(codec)
    sender.enable_encryption(bytes(range(32)))
    receiver.enable_encryption(bytes(range(32)))
    packet = codec.decode_packet(golden(2, "test_002_play_status.cpp")).payload
    with pytest.raises(ValueError):
        sender.encode([])
    first, second = sender.encode([packet]), sender.encode([packet])
    assert first != second
    assert receiver.decode(first)[0].payload.status == packet.status
    corrupted = second[:-1] + bytes([second[-1] ^ 1])
    with pytest.raises(bp.DecodeError):
        receiver.decode(corrupted, recover_packet_errors=recover)
    with pytest.raises(RuntimeError, match="terminal"):
        receiver.decode(second)


@pytest.mark.parametrize("malformed", [b"\x02\x00", b"\x03\xff\xff\xff\xff\x10", b"\x04\x00"])
def test_body_recovery_is_explicit_owned_and_keeps_wire_order(malformed, golden):
    good = golden(2, "test_002_play_status.cpp")
    unknown = varuint(1023) + b"opaque"
    batch = BatchCodec(bp.Codec(2193))
    result = batch.decode(frame(good, malformed, unknown, good), recover_packet_errors=True)
    assert result.packet_count == result.decoded_count + len(result.skipped_packet_ids) + len(result.errors) == 4
    assert result.decoded_count == 3 and not result.filtered and result.skipped_packet_ids == ()
    assert isinstance(result[1].payload, bp.UnknownPacket)
    error = result.errors[0]
    assert error.protocol == 2193 and error.packet_index == 1
    assert error.header.packet_id == malformed[0]
    assert 1 <= error.offset <= len(malformed) and error.reason
    with pytest.raises(AttributeError):
        error.reason = "changed"
    assert len(batch.decode(frame(good), recover_packet_errors=True)) == 1
    del batch, result
    gc.collect()
    assert error.header.packet_id == malformed[0] and error.reason
    strict = BatchCodec(bp.Codec(2193))
    with pytest.raises(bp.DecodeError):
        strict.decode(frame(good, malformed, good))
    with pytest.raises(RuntimeError, match="terminal"):
        strict.decode(frame(good), recover_packet_errors=True)


def test_recovery_errors_and_filter_skips_are_distinct(golden):
    good = golden(2, "test_002_play_status.cpp")
    result = BatchCodec(bp.Codec(2193)).decode(
        frame(b"\x09", b"\x02", good, b"\x02\x00"), packet_ids={2}, recover_packet_errors=True
    )
    assert result.skipped_packet_ids == (9,) and result.filtered
    assert [error.packet_index for error in result.errors] == [1, 3]
    assert result.packet_count == result.decoded_count + len(result.skipped_packet_ids) + len(result.errors)


@pytest.mark.parametrize("position", [0, 1, 2])
def test_recovery_still_validates_every_header_before_any_body(position, golden):
    good = golden(2, "test_002_play_status.cpp")
    packets = [good, b"\x02", good]
    packets[position] = varuint(1 << 14)
    batch = BatchCodec(bp.Codec(2193))
    with pytest.raises(bp.DecodeError, match="reserved_packet_header_bits"):
        batch.decode(frame(*packets), recover_packet_errors=True)
    with pytest.raises(RuntimeError, match="terminal"):
        batch.decode(frame(good))


@pytest.mark.parametrize(
    "algorithm,invalid",
    [
        (None, b""), (None, b"\x80"), (None, bytes.fromhex("ffffffff10")), (None, b"\x01\x80"),
        (Compression.ZLIB, b"\x00x"), (Compression.SNAPPY, b"\x01x"), (Compression.NONE, b"\xff\x80"),
    ],
)
def test_wire_and_compression_failures_are_terminal(algorithm, invalid):
    batch = BatchCodec(bp.Codec(2193))
    if algorithm is not None:
        batch.set_compression(algorithm, 0)
    with pytest.raises(bp.DecodeError):
        batch.decode(invalid, recover_packet_errors=True)
    with pytest.raises(RuntimeError, match="terminal"):
        batch.decode(frame(b"\x04"))


@pytest.mark.parametrize(
    "limits",
    [bp.DecodeLimits(max_depth=0), bp.DecodeLimits(max_decoded_bytes=0), bp.DecodeLimits(max_decoded_elements=0)],
)
def test_recovery_never_recovers_resource_failure(limits, golden):
    data = golden(136, "test_136_client_cache_miss_response.cpp")
    batch = BatchCodec(bp.Codec(2193, limits=limits))
    with pytest.raises(bp.DecodeError):
        batch.decode(frame(data), recover_packet_errors=True)
    with pytest.raises(RuntimeError, match="terminal"):
        batch.decode(frame(data))


def test_recovered_body_does_not_refund_cumulative_budget(golden):
    data = golden(136, "test_136_client_cache_miss_response.cpp")
    codec = bp.Codec(2193, limits=bp.DecodeLimits(max_decoded_elements=3))
    result = BatchCodec(codec).decode(frame(data + b"trailing"), recover_packet_errors=True)
    assert len(result.errors) == 1 and result.errors[0].reason == "trailing_packet_data"
    batch = BatchCodec(codec)
    with pytest.raises(bp.DecodeError):
        batch.decode(frame(data + b"trailing", data), recover_packet_errors=True)
    with pytest.raises(RuntimeError, match="terminal"):
        batch.decode(frame(data))


def test_recovery_treats_body_storage_budget_failure_as_fatal():
    packet = bp.v2193.ServerToClientHandshakePacket(token="x" * 100)
    data = bp.Codec(2193).encode_packet(packet)
    batch = BatchCodec(bp.Codec(2193, limits=bp.DecodeLimits(max_decoded_bytes=64)))
    with pytest.raises(bp.DecodeError):
        batch.decode(frame(data), recover_packet_errors=True)
    with pytest.raises(RuntimeError, match="terminal"):
        batch.decode(frame(data))


def test_recovery_preserves_encrypted_stream_after_body_error():
    sender = BatchCodec(bp.Codec(729))
    receiver = BatchCodec(bp.Codec(2225))
    sender.enable_encryption(bytes(range(32)))
    receiver.enable_encryption(bytes(range(32)))
    # 353 is unknown in 729, but has a required body in 2225.
    malformed = bp.UnknownPacket(packet_id=353, body=b"")
    unknown = bp.UnknownPacket(packet_id=1023, body=b"next")
    first, second = sender.encode([malformed]), sender.encode([unknown])
    result = receiver.decode(first, recover_packet_errors=True)
    assert result.decoded_count == 0 and len(result.errors) == 1
    assert result.errors[0].header.packet_id == 353
    assert receiver.decode(second)[0].payload.body.to_bytes() == b"next"


def test_recovery_argument_validation_does_not_poison_codec(golden):
    batch = BatchCodec(bp.Codec(2193))
    good = frame(golden(2, "test_002_play_status.cpp"))
    with pytest.raises(ValueError, match="10 bits"):
        batch.decode(good, packet_ids={1024}, recover_packet_errors=True)
    with pytest.raises(TypeError):
        batch.decode(good, recover_packet_errors="yes")
    with pytest.raises(TypeError):
        batch.decode(object(), recover_packet_errors=True)
    assert len(batch.decode(good)) == 1


_SNAPSHOT_ALLOCATION_FAILURE_CASE = """
import os
import resource

import bedrock_protocol as bp
from bedrock_protocol.wire import BatchCodec

# Warm the bindings and packet table before constraining allocations.
good = b"\\x02\\x03\\x00"
assert len(BatchCodec(bp.Codec(2193)).decode(good)) == 1
batch = BatchCodec(bp.Codec(2193))
data = bytes(24 * 1024 * 1024)
old_limit = resource.getrlimit(resource.RLIMIT_AS)
with open("/proc/self/statm") as statm:
    virtual_bytes = int(statm.read().split()[0]) * os.sysconf("SC_PAGE_SIZE")
limit = virtual_bytes + 4 * 1024 * 1024
if old_limit[0] != resource.RLIM_INFINITY:
    limit = min(limit, old_limit[0])
if old_limit[1] != resource.RLIM_INFINITY:
    limit = min(limit, old_limit[1])
try:
    resource.setrlimit(resource.RLIMIT_AS, (limit, old_limit[1]))
    try:
        batch.decode(data, recover_packet_errors=True)
    except MemoryError:
        pass
    else:
        raise AssertionError("input snapshot did not fail allocation")
finally:
    resource.setrlimit(resource.RLIMIT_AS, old_limit)
try:
    batch.decode(good)
except RuntimeError as error:
    assert "terminal" in str(error)
else:
    raise AssertionError("snapshot allocation failure left codec usable")
"""


@pytest.mark.skipif(sys.platform != "linux", reason="requires Linux RLIMIT_AS and /proc VMS accounting")
def test_input_snapshot_allocation_failure_is_terminal(tmp_path):
    result = subprocess.run(
        [sys.executable, "-I", "-c", _SNAPSHOT_ALLOCATION_FAILURE_CASE],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"child exit {result.returncode}\n{result.stdout}\n{result.stderr}"


def test_prepared_generator_temporaries_retain_each_packet():
    def tokens():
        for i in range(257):
            yield bp.Codec(2193).prepare_packet(bp.UnknownPacket(packet_id=1023, body=i.to_bytes(2, "little") * 37))

    expected = [varuint(1023) + i.to_bytes(2, "little") * 37 for i in range(257)]
    batch = BatchCodec(bp.Codec(2193))
    encoded = batch.encode_prepared(tokens())
    assert encoded == frame(*expected)
    assert [packet.payload.body.to_bytes() for packet in batch.decode(encoded)] == [p[2:] for p in expected]


@pytest.mark.parametrize(
    "failure", ["type", "protocol", "iterator", "getiter", "count", "empty", "aggregate", "framing"]
)
def test_prepared_validation_does_not_advance_encryption(failure):
    codec = bp.Codec(2193)
    good = codec.prepare_packet(bp.UnknownPacket(packet_id=1023, body=b"next"))
    sender, control, receiver = (BatchCodec(codec) for _ in range(3))
    for batch in (sender, control, receiver):
        batch.enable_encryption(bytes(range(32)))

    def raising():
        yield good
        raise LookupError("iterator failed")

    class NoIterator:
        def __iter__(self):
            raise LookupError("getiter failed")

    error = ValueError
    reason = None
    if failure == "type":
        invalid, error = [good, bp.UnknownPacket(packet_id=1023, body=b"")], TypeError
    elif failure == "protocol":
        wrong_protocol = bp.Codec(1001).prepare_packet(bp.UnknownPacket(packet_id=1023, body=b""))
        invalid, error = [good, wrong_protocol], bp.EncodeError
        reason = "prepared_packet_protocol_mismatch"
    elif failure == "iterator":
        invalid, error = raising(), LookupError
    elif failure == "getiter":
        invalid, error = NoIterator(), LookupError
    elif failure == "count":
        invalid = (good for _ in range(4097))
    elif failure == "empty":
        invalid = iter(())
    else:
        large = codec.prepare_packet(bp.UnknownPacket(packet_id=1023, body=b"x" * (4 * 1024 * 1024 - 2)))
        invalid, error = [large] * (5 if failure == "aggregate" else 4), bp.EncodeError
        reason = "batch_byte_limit" if failure == "aggregate" else "batch exceeds byte limit"
    with pytest.raises(error) as caught:
        sender.encode_prepared(invalid)
    if reason is not None:
        assert caught.value.reason == reason
        assert caught.value.protocol == 2193
        assert caught.value.packet_id == (1023 if failure == "protocol" else None)
        assert caught.value.offset is None
    first = sender.encode_prepared([good])
    assert first == control.encode_prepared([good])
    assert receiver.decode(first)[0].payload.body.to_bytes() == b"next"
    second = sender.encode_prepared([good])
    assert second == control.encode_prepared([good]) and second != first
    assert receiver.decode(second)[0].payload.body.to_bytes() == b"next"


def test_prepared_packet_and_count_limit_boundaries():
    codec = bp.Codec(2193)
    batch = BatchCodec(codec)
    minimal = codec.prepare_packet(bp.UnknownPacket(packet_id=1023, body=b""))
    assert batch.encode_prepared([minimal] * 4096) == frame(*([varuint(1023)] * 4096))
    data = varuint(1023) + b"x" * (4 * 1024 * 1024 - 2)
    largest = codec.prepare_packet(bp.UnknownPacket(packet_id=1023, body=data[2:]))
    assert len(largest) == 4 * 1024 * 1024
    assert batch.encode_prepared([largest]) == frame(data)


def test_prepared_respects_thread_reentrancy_and_terminal_state():
    codec = bp.Codec(2193)
    prepared = codec.prepare_packet(bp.UnknownPacket(packet_id=1023, body=b"owned"))
    batch = BatchCodec(codec)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(RuntimeError, match="owner thread"):
            pool.submit(batch.encode_prepared, [prepared]).result()

    def reentrant():
        batch.encode_prepared([prepared])
        yield prepared

    with pytest.raises(RuntimeError, match="reentrant"):
        batch.encode_prepared(reentrant())
    assert batch.encode_prepared([prepared]) == frame(varuint(1023) + b"owned")
    with pytest.raises(bp.DecodeError):
        batch.decode(b"\x80")
    with pytest.raises(RuntimeError, match="terminal"):
        batch.encode_prepared([prepared])


@pytest.mark.parametrize("header", [b"\x82\x80\x00", varuint(2 | (2 << 10) | (3 << 12))])
@pytest.mark.parametrize("body", [b"\x00", b"\x00\x00\x00\x03trailing"])
def test_batch_recovery_matches_full_frame_error_offsets(header, body, golden):
    codec = bp.Codec(2193)
    data = header + body
    with pytest.raises(bp.DecodeError) as caught:
        codec.decode_packet(data)
    good = golden(2, "test_002_play_status.cpp")
    result = BatchCodec(codec).decode(frame(good, data, good), recover_packet_errors=True)
    assert (result.packet_count, result.decoded_count, len(result.errors)) == (3, 2, 1)
    error = result.errors[0]
    assert (error.offset, error.reason) == (caught.value.offset, caught.value.reason)
    assert error.packet_index == 1 and error.header.packet_id == 2
    assert error.offset >= len(header)
    assert (error.header.sender_subclient_id, error.header.target_subclient_id) == (
        (0, 0) if header == b"\x82\x80\x00" else (2, 3)
    )


@pytest.mark.parametrize("recover", [False, True])
def test_later_header_failure_precedes_body_resource_failure(recover, golden):
    resource_body = golden(136, "test_136_client_cache_miss_response.cpp")
    codec = bp.Codec(2193, limits=bp.DecodeLimits(max_decoded_elements=0))
    with pytest.raises(bp.DecodeError) as caught:
        BatchCodec(codec).decode(frame(resource_body, varuint(1 << 14)), recover_packet_errors=recover)
    assert caught.value.reason == "reserved_packet_header_bits"
    assert caught.value.packet_id is None and caught.value.offset == len(varuint(1 << 14))


def test_batch_reuses_noncanonical_header_offset_for_unknown_packet():
    data = b"\xff\x87\x00opaque"
    result = BatchCodec(bp.Codec(2193)).decode(frame(data))
    assert result.headers[0].packet_id == 1023
    assert result[0].payload.body.to_bytes() == b"opaque"
