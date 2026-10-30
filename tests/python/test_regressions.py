import gc
from enum import IntEnum
from uuid import UUID

import pytest
from conftest import varuint

import bedrock_protocol as bp
from bedrock_protocol.wire import BatchCodec


@pytest.mark.parametrize("length", [0, 1, 15, 17, 32])
def test_uuid_subclass_bytes_must_have_exact_native_length(length):
    class ForgedUUID(UUID):
        @property
        def bytes(self):
            return bytes(length)

    with pytest.raises(ValueError):
        bp.v2193.PackIdVersion(id=ForgedUUID(int=0), version=bp.v2193.SemVersion(version="1"))


@pytest.mark.parametrize("value", [0, 7, 1 << 64, (1 << 65) - 1, -1, 1 << 65])
@pytest.mark.parametrize("forged_bytes", [b"", bytes(9), b"\xff" * 9])
def test_bitset_subclasses_use_their_integer_value(value, forged_bytes, golden):
    calls = []

    class ForgedInt(int):
        def __int__(self):
            raise AssertionError("overridden __int__ called")

        def __index__(self):
            raise AssertionError("overridden __index__ called")

        def __lt__(self, other):
            calls.append("lt")
            return False

        def bit_length(self):
            calls.append("bit_length")
            return 0

        def to_bytes(self, *args):
            calls.append("to_bytes")
            return forged_bytes

    original = bp.Codec(1001).decode_packet(golden(144, "test_144_player_auth_input.cpp")).payload
    fields = {name: getattr(original, name) for name in original.to_dict()}
    if value == (1 << 65) - 1:
        codec = bp.Codec(1001)
        gated = codec.decode_packet(golden(144, "test_144_player_auth_input.cpp", occurrence=1)).payload
        interaction = codec.decode_packet(golden(144, "test_144_player_auth_input.cpp", occurrence=2)).payload
        fields.update(
            item_use_transaction=interaction.item_use_transaction,
            item_stack_request=gated.item_stack_request,
            player_block_actions=gated.player_block_actions,
            vehicle_rot=gated.vehicle_rot,
            client_predicted_vehicle=gated.client_predicted_vehicle,
        )
    fields["input_data"] = ForgedInt(value)
    if value < 0 or value >= 1 << 65:
        with pytest.raises(ValueError):
            bp.v1001.PlayerAuthInputPacket(**fields)
    else:
        packet = bp.v1001.PlayerAuthInputPacket(**fields)
        assert packet.input_data == value
    assert calls == []


def test_bitset_accepts_int_enum_but_rejects_bool(golden):
    class Flag(IntEnum):
        JUMP = 1

    original = bp.Codec(1001).decode_packet(golden(144, "test_144_player_auth_input.cpp")).payload
    fields = {name: getattr(original, name) for name in original.to_dict()}
    fields["input_data"] = Flag.JUMP
    assert bp.v1001.PlayerAuthInputPacket(**fields).input_data == 1
    fields["input_data"] = True
    with pytest.raises(TypeError):
        bp.v1001.PlayerAuthInputPacket(**fields)


class CallbackBuffer:
    def __init__(self, callback):
        self.callback = callback

    def __buffer__(self, flags):
        self.callback()
        return memoryview(b"outer")


class CallbackList(list):
    def __init__(self, callback, items):
        super().__init__(items)
        self.callback = callback

    def __iter__(self):
        self.callback()
        return super().__iter__()


@pytest.mark.parametrize("kind", ["record", "sequence", "unknown", "nbt", "variant"])
def test_recursive_conversion_cannot_publish_or_replace_partial_values(kind):
    if kind == "record":
        cls = bp.v2193.MissingBlobData
        inner = dict(blob_id=2, blob_data=b"inner")

        def arguments(callback):
            return dict(blob_id=1, blob_data=CallbackBuffer(callback))

        def observe(value):
            return value.blob_data.to_bytes()

        expected = b"outer"
    elif kind == "sequence":
        cls = bp.v2193.ClientCacheMissResponsePacket
        blob = bp.v2193.MissingBlobData(blob_id=1, blob_data=b"outer")
        inner = dict(blobs=[])

        def arguments(callback):
            return dict(blobs=CallbackList(callback, [blob]))

        def observe(value):
            return value.blobs[0].blob_data.to_bytes()

        expected = b"outer"
    elif kind == "unknown":
        cls = bp.UnknownPacket
        inner = dict(packet_id=1023, body=b"inner")

        def arguments(callback):
            return dict(packet_id=1023, body=CallbackBuffer(callback))

        def observe(value):
            return value.body.to_bytes()

        expected = b"outer"
    elif kind == "nbt":
        cls = bp.Nbt
        inner = dict(type=bp.NbtType.BYTE_ARRAY, value=b"inner")

        def arguments(callback):
            return dict(type=bp.NbtType.BYTE_ARRAY, value=CallbackBuffer(callback))

        def observe(value):
            return bytes(memoryview(value))

        expected = b"outer"
    else:
        cls = bp.Variant
        inner = dict(index=0, value=b"inner")

        def arguments(callback):
            return dict(index=1, value=CallbackList(callback, [b"outer"]))

        def observe(value):
            return value.value

        expected = (b"outer",)

    victim = cls.__new__(cls)
    published = []

    def observe_partial():
        if kind == "nbt":
            return observe(victim)
        with pytest.warns(
            RuntimeWarning, match=r"^nanobind: attempted to access an uninitialized instance of type '[^']+'!$"
        ):
            return observe(victim)

    def reenter():
        cls.__init__(victim, **inner)
        try:
            published.append(observe_partial())
        except (TypeError, RuntimeError, BufferError):
            pass

    # Manual initialization cannot make an exposed empty allocation usable.
    cls.__init__(victim, **arguments(reenter))
    with pytest.raises((TypeError, RuntimeError, BufferError)):
        observe_partial()
    assert published == []

    outer = cls(**arguments(reenter))
    assert observe(outer) == expected
    assert published == []
    retained = observe(outer)
    cls.__init__(outer, **inner)
    assert observe(outer) == retained
    del outer
    victim = None
    gc.collect()
    assert retained == expected


def test_failed_and_nested_factory_conversion_preserves_owned_values():
    cls = bp.v2193.MissingBlobData
    nested = []

    def convert():
        nested.append(cls(blob_id=2, blob_data=b"retained"))
        raise ValueError("conversion failed")

    with pytest.raises(ValueError, match="conversion failed"):
        cls(blob_id=1, blob_data=CallbackBuffer(convert))
    gc.collect()
    assert nested[0].blob_data.to_bytes() == b"retained"
    assert cls(blob_id=3, blob_data=b"next").blob_id == 3


def test_decode_limits_cannot_be_reinitialized():
    limits = bp.DecodeLimits(max_depth=7)
    limits.__init__(max_depth=12)
    assert limits.max_depth == 7


@pytest.mark.parametrize("element_type", [bp.NbtType.END, bp.NbtType.INT])
def test_empty_nbt_list_preserves_explicit_type(element_type):
    value = bp.Nbt(bp.NbtType.LIST, [], element_type=element_type)
    assert value.element_type == element_type
    assert len(value) == 0


@pytest.mark.parametrize("element_type", [bp.NbtType.END, bp.NbtType.INT])
def test_nbt_list_rejects_conflicting_element_type(element_type):
    with pytest.raises((ValueError, RuntimeError)):
        bp.Nbt(bp.NbtType.LIST, [bp.Nbt(bp.NbtType.BYTE, 1)], element_type=element_type)


@pytest.mark.parametrize("wire,expected", [(b"\xff\xff\x03", -32768), (b"\xfe\xff\x03", 32767)])
def test_integral_narrowing_accepts_int16_limits(wire, expected, golden):
    data = golden(148, "test_148_item_stack_response.cpp", "golden_ok")[:-1] + wire
    payload = bp.Codec(1001).decode_packet(data).payload
    assert payload.responses[0].containers[0].slots[0].durability_correction == expected


@pytest.mark.parametrize("wire", [b"\x80\x80\x04", b"\x81\x80\x04"])
def test_integral_narrowing_rejects_int16_overflow_and_poison_batch(wire, golden):
    data = golden(148, "test_148_item_stack_response.cpp", "golden_ok")[:-1] + wire
    codec = bp.Codec(1001)
    with pytest.raises(bp.DecodeError):
        codec.decode_packet(data)
    batch = BatchCodec(codec)
    frame = varuint(len(data)) + data
    with pytest.raises(bp.DecodeError):
        batch.decode(frame)
    with pytest.raises(RuntimeError, match="terminal"):
        batch.decode(frame)


@pytest.mark.parametrize("value", [0, 255])
def test_construction_accepts_narrow_wire_integer_limits(value):
    packet = bp.v2193.PlayerToggleCrafterSlotRequestPacket(
        pos_x=0, pos_y=0, pos_z=0, slot_index=value, is_disabled=False
    )
    codec = bp.Codec(2193)
    assert codec.decode_packet(codec.encode_packet(packet)).payload.slot_index == value


@pytest.mark.parametrize("value", [-1, 256, 300])
def test_construction_rejects_integer_values_that_would_wrap_on_wire(value):
    with pytest.raises(TypeError, match="invalid field type or range"):
        bp.v2193.PlayerToggleCrafterSlotRequestPacket(
            pos_x=0, pos_y=0, pos_z=0, slot_index=value, is_disabled=False
        )


def test_construction_preserves_same_width_signed_unsigned_mapping():
    position = bp.v729.NetworkBlockPosition(x=0, y=-1, z=0)
    packet = bp.v729.BlockActorDataPacket(pos=position, data=bp.Nbt(bp.NbtType.COMPOUND, {}))
    codec = bp.Codec(729)
    decoded = codec.decode_packet(codec.encode_packet(packet)).payload
    assert decoded.pos.y == -1
    closed = bp.v729.ContainerClosePacket(
        container_id=bp.v729.ContainerID.NONE,
        container_type=bp.v729.ContainerType.NONE,
        server_initiated_close=False,
    )
    decoded = codec.decode_packet(codec.encode_packet(closed)).payload
    assert decoded.container_id is bp.v729.ContainerID.NONE
    assert decoded.container_type is bp.v729.ContainerType.NONE


def test_sequence_construction_obeys_its_own_length_prefix():
    old = bp.v1001.ResourcePackClientResponsePacket
    response = bp.v1001.ResourcePackResponse.DOWNLOADING
    packet = old(response=response, downloading_packs=[""] * 65535)
    codec = bp.Codec(1001)
    decoded = codec.decode_packet(codec.encode_packet(packet)).payload
    assert len(decoded.downloading_packs) == 65535
    assert decoded.downloading_packs[-1] == ""
    with pytest.raises(ValueError, match="length prefix"):
        old(response=response, downloading_packs=[""] * 65536)
    with pytest.raises(ValueError, match="length prefix"):
        old(response=response, downloading_packs=("" for _ in range(65536)))

    modern = bp.v2193.ResourcePackClientResponsePacket
    downloading = modern.Downloading(downloading_packs=[""] * 65536)
    packet = modern(response=bp.Variant(1, downloading))
    codec = bp.Codec(2193)
    decoded = codec.decode_packet(codec.encode_packet(packet)).payload
    assert len(decoded.response.value.downloading_packs) == 65536
    assert type(downloading.downloading_packs) is type(packet.response.value.downloading_packs)
