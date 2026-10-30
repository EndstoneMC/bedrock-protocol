import subprocess
import sys

import pytest
from conftest import varuint

import bedrock_protocol as bp
from bedrock_protocol.wire import BatchCodec

_MAPPING_CASE = """
import sys
if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
else:
    import resource
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
import bedrock_protocol as bp

kind, shape = sys.argv[1:]
item = "v" if kind == "map" else bp.Nbt(bp.NbtType.INT, 1)
arity = int(shape[-1])
entry = ("k", item, "extra")[:arity]
if shape.startswith("list"):
    entry = list(entry)
elif shape.startswith("forged"):
    class Pair(tuple):
        def __len__(self):
            return 0 if arity == 2 else 2
        def __getitem__(self, index):
            raise AssertionError("overridden tuple indexing called")
    entry = Pair(entry)
class Items:
    def items(self):
        yield entry
valid = arity == 2 and not shape.startswith("list")
try:
    if kind == "map":
        value = bp.v2193.SerializedRecipeIngredient(descriptor=Items(), aux_value=0, stack_size=1)
    else:
        value = bp.Nbt(bp.NbtType.COMPOUND, Items())
except TypeError as error:
    assert not valid
    assert str(error) == "items() must yield 2-tuples"
else:
    assert valid, "malformed mapping entry was accepted"
    if kind == "map":
        assert value.descriptor.to_dict() == {"k": "v"}
    else:
        assert value["k"].value == 1
"""


@pytest.mark.parametrize("kind", ["map", "nbt"])
@pytest.mark.parametrize(
    "shape", ["tuple0", "tuple1", "tuple2", "tuple3", "list2", "forged0", "forged1", "forged2", "forged3"]
)
def test_mapping_entries_use_actual_tuple_arity_and_items(kind, shape, tmp_path):
    result = subprocess.run(
        [sys.executable, "-I", "-c", _MAPPING_CASE, kind, shape],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"child exit {result.returncode}\n{result.stdout}\n{result.stderr}"


def _mapping_value(kind, source):
    if kind == "map":
        return bp.v2193.SerializedRecipeIngredient(descriptor=source, aux_value=0, stack_size=1)
    return bp.Nbt(bp.NbtType.COMPOUND, source)


def _mapping_item(kind):
    return "v" if kind == "map" else bp.Nbt(bp.NbtType.INT, 1)


def _mapping_read(kind, value, key):
    return value.descriptor[key] if kind == "map" else value[key].value


@pytest.mark.parametrize("kind", ["map", "nbt"])
def test_mapping_snapshots_temporary_generator_pairs(kind):
    released = []
    resumed = []
    item = _mapping_item(kind)

    class Pair(tuple):
        def __del__(self):
            released.append(True)

    class Items:
        def items(self):
            for key in ("a", "b"):
                yield Pair((key, item))
                resumed.append(key)

    value = _mapping_value(kind, Items())
    assert resumed == ["a", "b"]
    assert len(released) == 2
    assert _mapping_read(kind, value, "a") == ("v" if kind == "map" else 1)
    assert _mapping_read(kind, value, "b") == ("v" if kind == "map" else 1)


@pytest.mark.parametrize("kind", ["map", "nbt"])
@pytest.mark.parametrize("stage", ["items", "iteration", "conversion"])
def test_mapping_failure_never_publishes_partial_values(kind, stage):
    item = _mapping_item(kind)
    retained = _mapping_value(kind, {"retained": item})
    marker = LookupError("iteration failed")

    class Items:
        def items(self):
            if stage == "items":
                raise marker

            def entries():
                yield ("first", item)
                if stage == "iteration":
                    raise marker
                yield ("second", object())

            return entries()

    published = []
    expected = LookupError if stage != "conversion" else (TypeError if kind == "map" else RuntimeError)
    with pytest.raises(expected) as caught:
        published.append(_mapping_value(kind, Items()))
    if stage != "conversion":
        assert caught.value is marker
    assert published == []
    assert _mapping_read(kind, retained, "retained") == ("v" if kind == "map" else 1)
    assert _mapping_read(kind, _mapping_value(kind, {"next": item}), "next") == ("v" if kind == "map" else 1)


@pytest.mark.parametrize("levels,max_depth,accepted", [(8, 128, True), (8, 4, False), (128, 128, False)])
def test_nbt_construction_and_encoding_are_distinct_from_decode_budget(levels, max_depth, accepted):
    node = bp.Nbt(bp.NbtType.INT, 1)
    for _ in range(levels):
        node = bp.Nbt(bp.NbtType.COMPOUND, {"k": node})
    copied = node.copy()
    assert copied.wire_bytes() == node.wire_bytes()
    materialized = copied.to_dict()
    for _ in range(levels):
        assert materialized["type"] == "compound"
        materialized = materialized["value"]["k"]
    assert materialized == {"type": "int", "value": 1}
    packet = bp.v2193.BlockActorDataPacket(pos=bp.v2193.BlockPos(x=0, y=0, z=0), data=copied)
    wire = bp.Codec(2193).encode_packet(packet)
    codec = bp.Codec(2193, limits=bp.DecodeLimits(max_depth=max_depth))
    if accepted:
        assert codec.decode_packet(wire).payload.data.to_dict() == node.to_dict()
    else:
        with pytest.raises(bp.DecodeError) as caught:
            codec.decode_packet(wire)
        assert caught.value.protocol == 2193
        assert caught.value.packet_id == 56
        assert "large" in caught.value.reason.lower()


def _check_handshake_text(payload, raw):
    if raw == b"\xff":
        with pytest.raises(UnicodeDecodeError):
            _ = payload.token
        with pytest.raises(UnicodeDecodeError):
            payload.to_dict()
    else:
        assert payload.token == "a"
        assert payload.to_dict() == {"token": "a"}


@pytest.mark.parametrize("raw", [b"a", b"\xff"])
def test_text_conversion_is_lazy_and_native_reencoding_preserves_bytes(raw):
    wire = b"\x03\x01" + raw
    codec = bp.Codec(2193)
    payload = codec.decode_packet(wire).payload
    _check_handshake_text(payload, raw)
    assert payload.wire_bytes() == wire[1:]
    assert codec.encode_packet(payload) == wire
    assert codec.decode_packet(b"\x03\x01a").payload.token == "a"


@pytest.mark.parametrize("raw", [b"a", b"\xff"])
def test_text_conversion_failure_does_not_poison_batch_decode(raw):
    codec = bp.Codec(2193)
    batch = BatchCodec(codec)
    wire = b"\x03\x01" + raw
    frame = varuint(len(wire)) + wire
    payload = batch.decode(frame)[0].payload
    _check_handshake_text(payload, raw)
    assert codec.encode_packet(payload) == wire
    assert batch.encode([payload]) == frame
    assert batch.decode(b"\x03\x03\x01a")[0].payload.token == "a"
    with pytest.raises(bp.DecodeError):
        batch.decode(b"\x01\x02")
    with pytest.raises(RuntimeError, match="terminal"):
        batch.decode(b"\x03\x03\x01a")


@pytest.mark.parametrize("kind", ["string", "name"])
@pytest.mark.parametrize("invalid", [False, True])
def test_nested_nbt_text_converts_only_when_accessed(kind, invalid):
    name = b"\xff" if invalid and kind == "name" else b"key"
    text = b"\xff" if invalid and kind == "string" else b"a"
    wire = b"\x38\x00\x00\x00\x0a\x00\x0a\x05outer\x08"
    wire += varuint(len(name)) + name + varuint(len(text)) + text + b"\x00\x00"
    codec = bp.Codec(2193)
    payload = codec.decode_packet(wire).payload
    assert list(payload.data) == ["outer"]
    inner = payload.data["outer"]
    if invalid:
        expected = UnicodeDecodeError if kind == "string" else RuntimeError
        with pytest.raises(expected):
            if kind == "string":
                _ = inner["key"].value
            else:
                next(iter(inner))
        for value in (inner, payload.data, payload):
            with pytest.raises(expected):
                value.to_dict()
    else:
        assert list(inner) == ["key"]
        assert inner["key"].value == "a"
        assert inner.to_dict() == {"type": "compound", "value": {"key": {"type": "string", "value": "a"}}}
    assert codec.encode_packet(payload) == wire
    assert payload.wire_bytes() == wire[1:]


@pytest.mark.parametrize("kind", ["unknown", "binary"])
def test_non_utf8_opaque_bytes_remain_opaque(kind):
    codec = bp.Codec(2193)
    if kind == "unknown":
        packet = bp.UnknownPacket(packet_id=1023, body=b"\xff")
    else:
        packet = bp.v2193.ClientCacheMissResponsePacket(blobs=[bp.v2193.MissingBlobData(blob_id=9, blob_data=b"\xff")])
    wire = codec.encode_packet(packet)
    batch = BatchCodec(codec)
    payload = batch.decode(varuint(len(wire)) + wire)[0].payload
    if kind == "unknown":
        assert payload.body.to_bytes() == b"\xff"
    else:
        assert payload.blobs[0].blob_data.to_bytes() == b"\xff"
        assert payload.to_dict() == {"blobs": [{"blob_id": 9, "blob_data": b"\xff"}]}
    assert codec.encode_packet(payload) == wire
