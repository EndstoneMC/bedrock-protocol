import gc

import pytest
from conftest import varuint

import bedrock_protocol as bp

VERSIONS = (729, 748, 766, 776, 786, 800, 818, 819, 827, 844, 859, 898, 924, 944, 975, 1001, 2168, 2193, 2225)


def test_all_schema_versions_and_packet_counts():
    assert bp.SUPPORTED_VERSIONS == VERSIONS
    ids = [bp.Codec(v).supported_packet_ids for v in VERSIONS]
    assert sum(map(len, ids)) == 4079
    assert len(set().union(*ids)) == 245
    for version, supported in zip(VERSIONS, ids):
        assert supported == bp.Codec(version).known_packet_ids
        assert getattr(bp, f"v{version}").PlayStatusPacket is bp.v1001.PlayStatusPacket
    assert bp.v1001.PlayStatusPacket.__module__ == "bedrock_protocol.v1001"
    assert bp.v748.CameraInstructionPacket is bp.v766.CameraInstructionPacket
    assert bp.v748.CameraInstructionPacket.__module__ == "bedrock_protocol.v748"


def test_game_rule_owner_preserves_accepted_metadata_and_distinct_shapes():
    for name in ("GameRule", "GameRulesChangedPacketData"):
        canonical = getattr(bp.v2193, name)
        assert canonical.__module__ == "bedrock_protocol.v2193"
        assert canonical.__qualname__ == name
        for version in VERSIONS:
            current = getattr(getattr(bp, f"v{version}"), name)
            assert (current is canonical) == (version >= 844)
    assert bp.v1001.legacy.GameRule is not bp.v2193.GameRule
    assert bp.v1001.legacy.GameRule.__module__ == "bedrock_protocol.v1001"


def change(value, version=1001):
    return getattr(bp, f"v{version}").DataStoreChange(
        data_store_name="form", property="state", update_count=2, new_data=value
    )


@pytest.mark.parametrize(
    "tag,value",
    [(0, None), (1, True), (2, -7), (3, 0.25), (4, "hi"), (5, [bp.Variant(0, None)]), (6, {"x": bp.Variant(2, 7)})],
)
def test_dynamic_value_tags(tag, value):
    assert bp.v1001.DynamicValue is bp.Variant
    result = change(bp.Variant(tag, value)).new_data
    assert result.index == tag
    if tag < 5:
        assert result.value == value
    elif tag == 5:
        assert isinstance(result.value, bp.SequenceView)
        assert result.value[0].index == 0
    else:
        assert isinstance(result.value, bp.MapView)
        assert result.value["x"].value == 7


@pytest.mark.parametrize(
    "tag,value",
    [
        (0, False),
        (1, 1),
        (2, True),
        (2, 2**63),
        (2, -(2**63) - 1),
        (3, 1),
        (4, b"x"),
        (5, [1]),
        (6, {1: bp.Variant(0, None)}),
        (7, None),
    ],
)
def test_dynamic_value_rejects_wrong_arms(tag, value):
    with pytest.raises((TypeError, ValueError, OverflowError)):
        change(bp.Variant(tag, value))


def test_dynamic_golden_native_views_survive_owners(golden):
    codec = bp.Codec(1001)
    data = golden(330, "test_330_clientbound_data_store.cpp", "golden_nested")
    envelope = codec.decode_packet(data)
    assert codec.encode_packet(envelope.payload) == data
    mapping = envelope.payload.updates[0].value.new_data.value
    iterator = iter(mapping["items"].value)
    keys = iter(mapping)
    detached = mapping.copy()
    del mapping, envelope, codec
    gc.collect()
    assert next(iterator).value == "a"
    assert next(iterator).value == 7
    assert detached["ratio"].value == 0.25
    assert list(keys) == ["flag", "items", "nothing", "ratio"]
    with pytest.raises(TypeError):
        detached["flag"] = bp.Variant(1, False)


def test_photo_binary_golden(golden):
    data = golden(99, "test_099_photo_transfer.cpp")
    codec = bp.Codec(1001)
    payload = codec.decode_packet(data).payload
    photo = payload.photo_data
    assert isinstance(photo, bp.BinaryView)
    assert photo.to_bytes().startswith(b"\xff\xd8\xff\xe0")
    assert memoryview(photo).readonly
    assert codec.encode_packet(payload) == data


def test_compressed_biome_opaque_bytes_and_retirement():
    codec = bp.Codec(786)
    packet = bp.v786.CompressedBiomeDefinitionListPacket(compressed_biome_data=b"\xff\x00\xfe")
    wire = codec.encode_packet(packet)
    assert wire == varuint(301) + b"\x03\xff\x00\xfe"
    view = codec.decode_packet(wire).payload.compressed_biome_data
    del codec, packet
    gc.collect()
    assert view.to_bytes() == b"\xff\x00\xfe"
    assert memoryview(view).readonly
    assert not hasattr(bp.v800, "CompressedBiomeDefinitionListPacket")
    assert 301 not in bp.Codec(800).known_packet_ids


@pytest.mark.parametrize("version", [1001, 2225])
@pytest.mark.parametrize("variable,expected", [("golden", bytes.fromhex("deadbeef")), ("golden_fixed_widths", b"")])
def test_resource_pack_hash_binary_golden(version, variable, expected, golden):
    module = getattr(bp, f"v{version}")
    assert module.ResourcePackDataInfoPacket is bp.v1001.ResourcePackDataInfoPacket
    codec = bp.Codec(version)
    data = golden(82, "test_082_resource_pack_data_info.cpp", variable)
    envelope = codec.decode_packet(data)
    payload = envelope.payload
    assert payload.file_hash.to_bytes() == expected
    assert payload.to_dict()["file_hash"] == expected
    assert codec.encode_packet(payload) == data
    assert memoryview(payload.file_hash).readonly


@pytest.mark.parametrize("version", [1001, 2168])
@pytest.mark.parametrize("cached", [False, True])
def test_subchunk_binary_golden_and_presence(version, cached, golden):
    variable = f"golden_v{version}_{'cached' if cached else 'uncached'}"
    data = golden(174, "test_174_sub_chunk.cpp", variable)
    codec = bp.Codec(version)
    envelope = codec.decode_packet(data)
    packet = envelope.payload
    field = "uncached_sub_chunk_data" if version < 2168 and not cached else "sub_chunk_data"
    entry = getattr(packet, field)[0]
    expected = None if cached else b"\xaa"
    assert entry.to_dict()["serialized_sub_chunk"] == expected
    assert codec.encode_packet(packet) == data
    values = {name: getattr(entry, name) for name in entry.to_dict()}
    if expected is not None:
        source = bytearray(expected)
        values["serialized_sub_chunk"] = memoryview(source).toreadonly()
    rebuilt = type(entry)(**values)
    fields = {name: getattr(packet, name) for name in packet.to_dict()}
    fields[field] = [rebuilt]
    assert codec.encode_packet(type(packet)(**fields)) == data


def test_subchunk_conditional_absence_and_optional_empty_are_distinct(golden):
    for version in (1001, 2168):
        codec = bp.Codec(version)
        packet = codec.decode_packet(golden(174, "test_174_sub_chunk.cpp", f"golden_v{version}_cached")).payload
        entry = packet.sub_chunk_data[0]
        assert entry.serialized_sub_chunk is None
        fields = {name: getattr(entry, name) for name in entry.to_dict()}
        fields["serialized_sub_chunk"] = b""
        if version == 1001:
            with pytest.raises(ValueError, match="must be None"):
                type(entry)(**fields)
        else:
            values = {name: getattr(packet, name) for name in packet.to_dict()}
            values["sub_chunk_data"] = [type(entry)(**fields)]
            decoded = codec.decode_packet(codec.encode_packet(type(packet)(**values))).payload
            assert decoded.sub_chunk_data[0].serialized_sub_chunk.to_bytes() == b""


def nested(depth, value=None):
    result = value if value is not None else bp.Variant(0, None)
    for _ in range(depth - 1):
        result = bp.Variant(5, [result])
    return result


def test_dynamic_depth_native_subtrees_and_repeated_references():
    result = change(nested(128)).new_data
    with pytest.raises(ValueError, match="depth"):
        change(nested(129))
    with pytest.raises(ValueError, match="depth"):
        change(bp.Variant(5, [result]))
    mapping = change(bp.Variant(6, {"x": nested(127)})).new_data
    with pytest.raises(ValueError, match="depth"):
        change(bp.Variant(6, {"x": mapping}))
    repeated = bp.Variant(2, -(2**63))
    copied = change(bp.Variant(5, [repeated, repeated])).new_data.value
    assert [item.value for item in copied] == [-(2**63), -(2**63)]
    assert change(bp.Variant(2, 2**63 - 1)).new_data.value == 2**63 - 1
    assert change(bp.Variant(3, float("inf"))).new_data.value == float("inf")


def test_dynamic_materialized_cycles_and_detachment():
    source = change(bp.Variant(5, [bp.Variant(0, None)]))
    materialized = source.to_dict()["new_data"]
    materialized.value.append(materialized)
    with pytest.raises(ValueError, match="cyclic"):
        change(materialized)
    mapping = change(bp.Variant(6, {"x": bp.Variant(0, None)})).to_dict()["new_data"]
    mapping.value["x"] = mapping
    with pytest.raises(ValueError, match="cyclic"):
        change(mapping)
    detached = source.new_data.value.copy()
    data = source.to_dict()["new_data"].value
    data.clear()
    assert len(detached) == len(source.new_data.value) == 1
    with pytest.raises(TypeError):
        detached[0] = bp.Variant(0, None)


def test_dynamic_requires_matching_native_views():
    unrelated = bp.v1001.ClientCacheMissResponsePacket(blobs=[]).blobs
    with pytest.raises(TypeError):
        change(bp.Variant(5, unrelated))
    assert change(bp.Variant(True, True)).new_data.value is True


@pytest.mark.parametrize("version,arm", [(859, 0), (898, 1), (1001, 1), (2225, 1)])
def test_dynamic_packet_alternatives(version, arm):
    module = getattr(bp, f"v{version}")
    cls = module.DataStoreSyncPacket if version == 859 else module.ClientboundDataStorePacket
    packet = cls(updates=[bp.Variant(arm, change(bp.Variant(4, "state"), version))])
    codec = bp.Codec(version)
    wire = codec.encode_packet(packet)
    assert codec.decode_packet(wire).payload.updates[0].value.new_data.value == "state"
    assert wire[len(varuint(330)) + 1] == arm


@pytest.mark.parametrize("variable", ["golden", "golden_nested"])
def test_dynamic_independent_goldens(variable, golden):
    codec = bp.Codec(1001)
    data = golden(330, "test_330_clientbound_data_store.cpp", variable)
    assert codec.encode_packet(codec.decode_packet(data).payload) == data


def test_dynamic_invalid_native_tag(golden):
    data = golden(330, "test_330_clientbound_data_store.cpp", "golden_nested")
    assert data[19:23] == bytes.fromhex("06000000")
    invalid = data[:19] + bytes.fromhex("07000000") + data[23:]
    with pytest.raises(bp.DecodeError) as caught:
        bp.Codec(1001).decode_packet(invalid)
    assert caught.value.reason != "trailing_packet_data"
