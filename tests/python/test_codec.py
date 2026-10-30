import gc

import pytest
from conftest import varuint

import bedrock_protocol as bp
from bedrock_protocol.wire import BatchCodec


def test_runtime_entrypoint():
    assert 1001 in bp.SUPPORTED_VERSIONS and 2193 in bp.SUPPORTED_VERSIONS
    for protocol in bp.SUPPORTED_VERSIONS:
        codec = bp.Codec(protocol)
        assert codec.protocol == protocol
        assert codec.supported_packet_ids == codec.known_packet_ids
        with pytest.raises(AttributeError):
            codec.protocol = 729


@pytest.mark.parametrize("version", [0, 730, 2169, 2226, -1])
def test_unsupported_versions_reject_immediately(version):
    with pytest.raises(bp.UnsupportedVersionError) as caught:
        bp.Codec(version)
    assert caught.value.protocol == version
    assert caught.value.reason == "unsupported_protocol"


@pytest.mark.parametrize("protocol", [1001, 2193])
@pytest.mark.parametrize(
    "packet_id,filename,variable",
    [
        (2, "test_002_play_status.cpp", "golden"),
        (3, "test_003_server_to_client_handshake.cpp", "golden"),
        (69, "test_069_request_chunk_radius.cpp", "golden"),
        (70, "test_070_chunk_radius_updated.cpp", "golden"),
        (113, "test_113_set_local_player_as_initialized.cpp", "golden"),
        (115, "test_115_network_stack_latency.cpp", "golden"),
        (129, "test_129_client_cache_status.cpp", "golden"),
        (136, "test_136_client_cache_miss_response.cpp", "golden"),
        (193, "test_193_request_network_settings.cpp", "golden_1001"),
    ],
)
def test_independent_native_goldens(protocol, packet_id, filename, variable, golden):
    data = golden(packet_id, filename, variable)
    codec = bp.Codec(protocol)
    decoded = codec.decode_packet(data)
    assert decoded.protocol == protocol
    assert decoded.header.packet_id == packet_id
    assert decoded.payload.protocol == protocol
    assert decoded.payload.wire_bytes() == data[len(varuint(packet_id)) :]
    assert codec.encode_packet(decoded.payload) == data
    batch = BatchCodec(codec)
    prepared = codec.prepare_packet(decoded.payload)
    assert len(prepared) == len(data)
    assert batch.encode_prepared([prepared]) == batch.encode([decoded.payload]) == varuint(len(data)) + data
    subclient_data = varuint(packet_id | (2 << 10) | (3 << 12)) + data[len(varuint(packet_id)) :]
    assert codec.encode_packet(decoded.payload, sender_subclient_id=2, target_subclient_id=3) == subclient_data
    prepared = codec.prepare_packet(decoded.payload, sender_subclient_id=2, target_subclient_id=3)
    assert len(prepared) == len(subclient_data)
    assert batch.encode_prepared([prepared]) == varuint(len(subclient_data)) + subclient_data


def test_owned_keyword_constructor_and_shared_shape(golden):
    assert bp.v1001.PlayStatusPacket is bp.v2193.PlayStatusPacket
    assert bp.v1001.PlayStatus is bp.v2193.PlayStatus
    packet = bp.v2193.PlayStatusPacket(status=bp.v2193.PlayStatus.PLAYER_SPAWN)
    assert packet.protocol is None
    with pytest.raises(TypeError):
        bp.v2193.PlayStatusPacket()
    with pytest.raises(TypeError):
        bp.v2193.PlayStatusPacket(bp.v2193.PlayStatus.PLAYER_SPAWN)
    with pytest.raises((TypeError, RuntimeError)):
        bp.v2193.PlayStatusPacket(status=3)
    with pytest.raises(AttributeError):
        packet.status = bp.v2193.PlayStatus.LOGIN_SUCCESS
    expected = golden(2, "test_002_play_status.cpp")
    assert bp.Codec(1001).encode_packet(packet) == expected
    assert bp.Codec(2193).encode_packet(packet) == expected


@pytest.mark.parametrize("protocol", [729, 1001, 2193, 2225])
def test_packet_subclass_encodes_with_shared_shape(protocol, golden):
    class PlayStatusSubclass(bp.v1001.PlayStatusPacket):
        pass

    packet = PlayStatusSubclass(status=bp.v1001.PlayStatus.PLAYER_SPAWN)
    expected = golden(2, "test_002_play_status.cpp")
    codec = bp.Codec(protocol)
    assert codec.encode_packet(packet) == expected
    assert BatchCodec(codec).encode([packet]) == varuint(len(expected)) + expected


def test_open_enums_preserve_unknown_values_without_cache_growth():
    enum = bp.v2193.PlayStatus
    before = (len(enum.__members__), len(enum._value2member_map_))
    for value in range(1000, 1100):
        unknown = enum(value)
        assert unknown.name is None
        packet = bp.v2193.PlayStatusPacket(status=unknown)
        decoded = bp.Codec(2193).decode_packet(bp.Codec(2193).encode_packet(packet))
        assert type(decoded.payload.status) is enum
        assert decoded.payload.status == value
    assert before == (len(enum.__members__), len(enum._value2member_map_))
    with pytest.raises(ValueError):
        enum(1 << 32)


def test_subclient_header_fields(golden):
    codec = bp.Codec(2193)
    payload = codec.decode_packet(golden(2, "test_002_play_status.cpp")).payload
    wire = codec.encode_packet(payload, sender_subclient_id=2, target_subclient_id=3)
    result = codec.decode_packet(wire)
    assert (result.header.packet_id, result.header.sender_subclient_id, result.header.target_subclient_id) == (2, 2, 3)
    assert wire == varuint(2 | (2 << 10) | (3 << 12)) + payload.wire_bytes()
    with pytest.raises(ValueError):
        codec.encode_packet(payload, sender_subclient_id=4)


def test_unknown_and_invalid_known_are_distinct():
    codec = bp.Codec(2193)
    data = varuint(1023) + b"\xff\x00opaque"
    result = codec.decode_packet(data)
    assert isinstance(result.payload, bp.UnknownPacket)
    assert result.payload.body.to_bytes() == b"\xff\x00opaque"
    assert codec.encode_packet(result.payload) == data
    with pytest.raises(bp.DecodeError) as caught:
        codec.decode_packet(varuint(9))
    assert caught.value.packet_id == 9
    with pytest.raises(bp.DecodeError) as caught:
        codec.decode_packet(varuint(2) + b"\x00")
    assert caught.value.packet_id == 2
    with pytest.raises(bp.EncodeError, match="known_packet"):
        codec.encode_packet(bp.UnknownPacket(packet_id=2, body=b"\x00\x00\x00\x03"))


@pytest.mark.parametrize("protocol", bp.SUPPORTED_VERSIONS)
def test_header_only_packet_id_classification(protocol):
    codec = bp.Codec(protocol)
    supported = set(codec.supported_packet_ids)
    for packet_id in range(1024):
        try:
            decoded = codec.decode_packet(varuint(packet_id))
        except bp.DecodeError as error:
            assert packet_id in supported
            assert error.protocol == protocol
            assert error.packet_id == packet_id
            assert error.reason != "packet_not_bound"
        else:
            assert decoded.protocol == protocol
            assert decoded.header.packet_id == packet_id
            payload = decoded.payload
            if packet_id in supported:
                assert not isinstance(payload, bp.UnknownPacket)
            else:
                assert isinstance(payload, bp.UnknownPacket)
                assert payload.packet_id == packet_id
                assert payload.body.to_bytes() == b""


def test_conditional_fields_are_explicit_and_shape_checked(golden):
    codec = bp.Codec(1001)
    data = golden(58, "test_058_level_chunk.cpp", "golden_v1001_full")
    chunk = codec.decode_packet(data).payload
    assert chunk.client_request_sub_chunk_limit is None
    assert chunk.cache_metadata is None
    kwargs = dict(
        pos=chunk.pos,
        dimension_id=chunk.dimension_id,
        sub_chunks_count=chunk.sub_chunks_count,
        client_request_sub_chunk_limit=None,
        cache_enabled=False,
        cache_metadata=None,
        serialized_chunk=chunk.serialized_chunk,
    )
    packet = bp.v1001.LevelChunkPacket(**kwargs)
    assert codec.encode_packet(packet) == data
    kwargs["cache_metadata"] = []
    with pytest.raises(ValueError, match="must be None"):
        bp.v1001.LevelChunkPacket(**kwargs)
    with pytest.raises(bp.EncodeError, match="packet_type_unavailable"):
        bp.Codec(2193).encode_packet(packet)


def test_literal_and_variant_identity():
    v = bp.v2193
    assert bp.v1001.TransactionData is bp.Variant
    assert v.TransactionData is bp.Variant
    scalar = v.DataItemBytePayload(value=-2)
    assert scalar.type == v.DataItemType.BYTE
    with pytest.raises(TypeError):
        v.DataItemBytePayload(type=v.DataItemType.BYTE, value=-2)
    item = v.DataItemEntry(id=1, payload=bp.Variant(0, scalar))
    assert item.payload.index == 0
    assert item.payload.value.value == -2
    with pytest.raises((TypeError, RuntimeError)):
        v.DataItemEntry(id=1, payload=scalar)
    with pytest.raises(ValueError):
        v.DataItemEntry(id=1, payload=bp.Variant(99, scalar))
    with pytest.raises((TypeError, RuntimeError)):
        v.DataItemEntry(id=1, payload=bp.Variant(1, scalar))


def test_malformed_packet_limits_and_full_consumption(golden):
    codec = bp.Codec(2193)
    valid = golden(2, "test_002_play_status.cpp")
    for data in [
        b"",
        valid[:-1],
        valid + b"\x00",
        b"\xff\xff\xff\xff\x10",
        varuint(1 << 14),
        varuint(3) + b"\xff\xff\xff\xff\x0f",
        b"x" * (4 * 1024 * 1024 + 1),
    ]:
        with pytest.raises(bp.DecodeError):
            codec.decode_packet(data)
    with pytest.raises(bp.DecodeError):
        bp.Codec(2193, limits=bp.DecodeLimits(max_decoded_elements=0)).decode_packet(
            golden(136, "test_136_client_cache_miss_response.cpp")
        )
    with pytest.raises(bp.DecodeError):
        bp.Codec(2193, limits=bp.DecodeLimits(max_decoded_bytes=1)).decode_packet(valid)
    with pytest.raises(ValueError):
        bp.DecodeLimits(max_depth=129)


def test_codec_independent_calls_across_threads(golden):
    from concurrent.futures import ThreadPoolExecutor

    codec = bp.Codec(2193)
    data = golden(136, "test_136_client_cache_miss_response.cpp")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(codec.decode_packet, [data] * 20))
    assert [p.payload.blobs[0].blob_data.to_bytes() for p in results] == [b"chunk"] * 20


def test_bitset_width_and_explicit_none_constructor(golden):
    codec = bp.Codec(1001)
    data = golden(144, "test_144_player_auth_input.cpp")
    payload = codec.decode_packet(data).payload
    values = {name: getattr(payload, name) for name in payload.to_dict()}
    assert values["item_use_transaction"] is None
    assert values["item_stack_request"] is None
    assert codec.encode_packet(bp.v1001.PlayerAuthInputPacket(**values)) == data
    values["input_data"] = 1 << 64
    packet = bp.v1001.PlayerAuthInputPacket(**values)
    assert codec.decode_packet(codec.encode_packet(packet)).payload.input_data == 1 << 64
    values["input_data"] = 1 << 65
    with pytest.raises(ValueError, match="bitset"):
        bp.v1001.PlayerAuthInputPacket(**values)


def test_numeric_enum_wire_values_cannot_collapse_into_underlying_range(golden):
    codec = bp.Codec(2193)
    data = golden(49, "test_049_inventory_content.cpp", "golden_v2168")
    payload = codec.decode_packet(data).payload
    bad = data[:1] + varuint(300) + data[2:]
    with pytest.raises(bp.DecodeError):
        codec.decode_packet(bad)
    values = {name: getattr(payload, name) for name in payload.to_dict()}
    values["inventory_id"] = bp.v2193.ContainerID(-2)
    packet = bp.v2193.InventoryContentPacket(**values)
    assert codec.decode_packet(codec.encode_packet(packet)).payload.inventory_id == -2


@pytest.mark.parametrize("protocol", bp.SUPPORTED_VERSIONS)
def test_prepared_packet_all_versions_owns_immutable_encoding(protocol, golden):
    expected = golden(2, "test_002_play_status.cpp")
    codec = bp.Codec(protocol)
    packet = codec.decode_packet(expected).payload
    prepared = codec.prepare_packet(packet)
    assert isinstance(prepared, bp.EncodedPacket)
    assert (prepared.protocol, prepared.packet_id, len(prepared)) == (protocol, 2, len(expected))
    for name, value in [("protocol", 0), ("packet_id", 0), ("bytes", b"changed")]:
        with pytest.raises(AttributeError):
            setattr(prepared, name, value)
    with pytest.raises(TypeError):
        bp.EncodedPacket()
    with pytest.raises(TypeError):
        memoryview(prepared)
    del packet, codec
    gc.collect()
    assert BatchCodec(bp.Codec(protocol)).encode_prepared([prepared]) == varuint(len(expected)) + expected


@pytest.mark.parametrize(
    "kwargs", [{"sender_subclient_id": -1}, {"sender_subclient_id": 4}, {"target_subclient_id": 4}]
)
def test_prepare_preserves_subclient_validation(kwargs):
    codec = bp.Codec(2193)
    packet = bp.v2193.PlayStatusPacket(status=bp.v2193.PlayStatus.PLAYER_SPAWN)
    for encode in (codec.encode_packet, codec.prepare_packet):
        with pytest.raises(ValueError, match="subclient IDs must fit 2 bits"):
            encode(packet, **kwargs)


@pytest.mark.parametrize("case", ["type", "known_unknown", "packet_bytes"])
def test_prepare_preserves_encode_error_metadata(case):
    codec = bp.Codec(2193)
    packet = {
        "type": object,
        "known_unknown": lambda: bp.UnknownPacket(packet_id=2, body=b""),
        "packet_bytes": lambda: bp.UnknownPacket(packet_id=1023, body=b"x" * (4 * 1024 * 1024)),
    }[case]()
    errors = []
    for encode in (codec.encode_packet, codec.prepare_packet):
        with pytest.raises(bp.EncodeError) as caught:
            encode(packet)
        errors.append((caught.value.protocol, caught.value.packet_id, caught.value.offset, caught.value.reason))
    assert errors[0] == errors[1]
