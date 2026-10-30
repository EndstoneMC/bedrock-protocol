import gc
from uuid import UUID

import pytest

import bedrock_protocol as bp


def test_retained_views_iterators_buffers_and_input_snapshot(golden):
    data = bytearray(golden(136, "test_136_client_cache_miss_response.cpp"))
    codec = bp.Codec(2193)
    decoded = codec.decode_packet(memoryview(data).toreadonly())
    sequence = decoded.payload.blobs
    iterator = iter(sequence)
    blob = next(iterator)
    binary = blob.blob_data
    buffer = memoryview(binary)
    data[:] = b"\x00" * len(data)
    codec.decode_packet(golden(136, "test_136_client_cache_miss_response.cpp", "golden_empty"))
    del data, codec, decoded, sequence, blob, binary
    gc.collect()
    assert buffer.readonly and buffer.format == "B"
    assert bytes(buffer) == b"chunk"
    assert next(iterator).blob_id == 300
    with pytest.raises(StopIteration):
        next(iterator)
    with pytest.raises(TypeError):
        buffer[0] = 0


def test_selected_subtree_copy_and_empty_buffer(golden):
    packet = bp.Codec(2193).decode_packet(golden(136, "test_136_client_cache_miss_response.cpp")).payload
    copied = packet.blobs[0].copy()
    empty = memoryview(packet.blobs[1].blob_data)
    iterator = iter(packet.blobs.copy())
    del packet
    gc.collect()
    assert copied.blob_data.to_bytes() == b"chunk"
    assert copied.protocol == 2193
    assert empty.readonly and empty.format == "B" and len(empty) == 0
    assert next(iterator).blob_id == 0x0102030405060708
    assert copied.to_dict() == {"blob_id": 0x0102030405060708, "blob_data": b"chunk"}


def test_constructor_snapshots_mutable_inputs():
    source = bytearray(b"\xff\x00blob")
    blob = bp.v2193.MissingBlobData(blob_id=9, blob_data=memoryview(source).toreadonly())
    blobs = [blob]
    packet = bp.v2193.ClientCacheMissResponsePacket(blobs=blobs)
    source[:] = b"x" * len(source)
    blobs.clear()
    assert packet.blobs[0].blob_data.to_bytes() == b"\xff\x00blob"
    assert packet.blobs[0].protocol is None
    with pytest.raises(IndexError):
        packet.blobs[1]
    assert packet.blobs[-1].blob_id == 9


def test_nbt_signed_empty_and_typed_list_ownership():
    signed = bp.Nbt(bp.NbtType.BYTE_ARRAY, [-128, -1, 0, 127])
    empty = bp.Nbt(bp.NbtType.BYTE_ARRAY, b"")
    typed = bp.Nbt(bp.NbtType.LIST, [], element_type=bp.NbtType.INT)
    root = bp.Nbt(bp.NbtType.COMPOUND, {"signed": signed, "typed": typed})
    retained = root["signed"]
    view = memoryview(retained)
    iterator = iter(root)
    copied = root["typed"].copy()
    del root, signed, retained, typed
    gc.collect()
    assert view.readonly and view.format == "b"
    assert list(view) == [-128, -1, 0, 127]
    assert memoryview(empty).format == "b" and len(memoryview(empty)) == 0
    assert list(iterator) == ["signed", "typed"]
    assert copied.element_type == bp.NbtType.INT
    assert copied.to_dict() == {"type": "list", "element_type": "int", "value": []}
    with pytest.raises(TypeError):
        bp.Nbt(bp.NbtType.LIST, [])


def test_nbt_empty_list_element_type_survives_packet_codec(golden):
    codec = bp.Codec(2193)
    packet = codec.decode_packet(golden(80, "test_080_update_trade.cpp")).payload
    values = {field: getattr(packet, field) for field in packet.to_dict()}
    values["data"] = bp.Nbt(
        bp.NbtType.COMPOUND,
        {
            "empty_ints": bp.Nbt(bp.NbtType.LIST, [], element_type=bp.NbtType.INT),
            "signed": bp.Nbt(bp.NbtType.BYTE_ARRAY, [-1]),
        },
    )
    result = codec.decode_packet(codec.encode_packet(bp.v2193.UpdateTradePacket(**values)))
    assert result.payload.data["empty_ints"].element_type == bp.NbtType.INT
    assert memoryview(result.payload.data["signed"]).tolist() == [-1]


def test_explicit_uuid_adapter():
    identifier = UUID("00112233-4455-6677-8899-aabbccddeeff")
    v = bp.v2193
    value = v.PackIdVersion(id=identifier, version=v.SemVersion(version="1.2.3"))
    assert value.id == identifier
    with pytest.raises((TypeError, RuntimeError)):
        v.PackIdVersion(id=str(identifier), version=v.SemVersion(version="1.2.3"))


def skin_values(v, mapping):
    image = v.SkinImage(width=1, height=1, image_bytes=bytes(4))
    return dict(
        id="id",
        play_fab_id="play",
        resource_patch="patch",
        image_data=image,
        animated_image_data=[],
        cape_image_data=image,
        geometry_data="geo",
        geometry_data_min_engine_version="1.0.0",
        animation_data="",
        cape_id="",
        full_id="id",
        arm_size=v.ArmSizeType.WIDE,
        skin_color=0,
        persona_pieces=[],
        piece_tint_colors=mapping,
        is_premium=False,
        is_persona=False,
        is_persona_cape_on_classic_skin=False,
        is_primary_user=True,
        overrides_player_appearance=False,
        trusted_skin_flag=v.TrustedSkinFlag.TRUE,
        profile_hash="hash",
    )


def test_map_views_iterators_and_typed_keys_own_their_storage():
    v = bp.v2193
    key = next(iter(v.PieceType))
    source = {key: v.TintMapColor(colors=[1, 2, 3, 4])}
    skin = v.SerializedSkinRef(**skin_values(v, source))
    source.clear()
    mapping = skin.piece_tint_colors
    iterator = iter(mapping)
    child = mapping[key].colors
    copied_skin = v.SerializedSkinRef(**skin_values(v, mapping))
    del skin, mapping
    gc.collect()
    assert next(iterator) is key
    assert child.to_list() == [1, 2, 3, 4]
    assert copied_skin.piece_tint_colors.to_dict() == {key: {"colors": [1, 2, 3, 4]}}
    with pytest.raises(KeyError):
        copied_skin.piece_tint_colors[v.PieceType(200)]
    with pytest.raises((TypeError, RuntimeError)):
        copied_skin.piece_tint_colors[0]


def test_name_coded_enums_reject_unnamed_values():
    v = bp.v2193
    values = skin_values(v, {v.PieceType(200): v.TintMapColor(colors=[1, 2, 3, 4])})
    with pytest.raises(ValueError, match="wire name"):
        v.SerializedSkinRef(**values)


def test_variant_none_snapshot_cycles_and_gc():
    assert bp.Variant(0, None).value is None
    assert bp.Nbt(bp.NbtType.END, None).value is None
    source = [bytearray(b"abc")]
    variant = bp.Variant(1, source)
    source[0][:] = b"xxx"
    assert variant.value == (b"abc",)
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(ValueError, match="cyclic"):
        bp.Variant(0, cyclic)
    packet = bp.v2193.DataItemEntry(id=1, payload=bp.Variant(0, bp.v2193.DataItemBytePayload(value=1)))
    materialized = packet.to_dict()["payload"]
    assert gc.is_tracked(materialized)
    materialized.value["cycle"] = materialized
    del materialized
    assert gc.collect() > 0
