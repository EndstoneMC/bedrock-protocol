"""What the generic binder promises beyond the codecs themselves."""

import importlib
import uuid

import pytest
from conftest import VERSIONS

proto = VERSIONS[0]


def uvarint(value):
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def test_the_bare_names_are_the_latest_protocol():
    import bedrock_protocol

    latest = importlib.import_module(f"bedrock_protocol.v{bedrock_protocol.LATEST_PROTOCOL}")
    assert bedrock_protocol.TextPacket is latest.TextPacket
    assert bedrock_protocol.PROTOCOL == bedrock_protocol.LATEST_PROTOCOL
    packet = bedrock_protocol.PlayStatusPacket(status=bedrock_protocol.PlayStatus.PLAYER_SPAWN)
    assert bedrock_protocol.decode(packet.ID, bedrock_protocol.encode(packet)) == packet


def test_the_header_packs_recipient_then_sender_as_bds_does():
    packet = proto.PlayStatusPacket(status=proto.PlayStatus.PLAYER_SPAWN)
    framed = proto.encode_packet(packet, recipient_sub_id=1, sender_sub_id=2)
    assert framed == uvarint(packet.ID | 1 << 10 | 2 << 12) + bytes(packet)
    header, back = proto.decode_packet(framed)
    assert (header.packet_id, header.recipient_sub_id, header.sender_sub_id) == (packet.ID, 1, 2)
    assert back == packet


def test_positionals_fill_fields_in_order_and_keywords_by_name():
    assert proto.Vec3(1, 2, z=3) == proto.Vec3(x=1, y=2, z=3)
    with pytest.raises(TypeError, match="multiple values"):
        proto.Vec3(1, x=2)
    with pytest.raises(TypeError, match="no field 'w'"):
        proto.Vec3(w=1)
    with pytest.raises(TypeError, match="at most 3"):
        proto.Vec3(1, 2, 3, 4)


def test_a_struct_field_is_a_live_reference_and_a_list_is_a_copy():
    packet = proto.MovePlayerPacket()
    pos = packet.pos
    packet.pos.x = 5.5
    assert pos.x == 5.5

    packet = proto.PlayerAuthInputPacket(input_data=[proto.PlayerAuthInputPacket.InputData.UP])
    packet.input_data.append(proto.PlayerAuthInputPacket.InputData.DOWN)
    assert packet.input_data == [proto.PlayerAuthInputPacket.InputData.UP]


def test_a_value_the_schema_does_not_name_crosses_as_an_int():
    packet = proto.PlayStatusPacket.from_bytes(bytes([0, 0, 0, 0xFF]))
    assert packet.status == 255 and type(packet.status) is int
    assert "status=255" in repr(packet)
    assert bytes(packet) == bytes([0, 0, 0, 0xFF])

    window = proto.ContainerClosePacket(container_id=5)
    assert window.container_id == 5
    assert proto.ContainerClosePacket.from_bytes(bytes(window)) == window
    window.container_id = proto.ContainerID.INVENTORY
    assert window.container_id is proto.ContainerID.INVENTORY
    with pytest.raises(TypeError):
        proto.ContainerClosePacket(container_id=1000)


def test_a_string_carries_any_bytes():
    raw = bytes([0xFF, 0x00, 0xC3, 0x41])
    packet = proto.LevelChunkPacket(serialized_chunk=raw)
    assert packet.serialized_chunk.encode("utf-8", "surrogateescape") == raw
    assert proto.LevelChunkPacket.from_bytes(bytes(packet)) == packet
    packet.serialized_chunk = "héllo"
    assert packet.serialized_chunk == "héllo"


def test_a_uuid_crosses_as_uuid():
    value = uuid.UUID("12345678-9abc-def0-1122-334455667788")
    request = proto.CommandRequestPacket().origin
    request.uuid = value
    assert request.uuid == value
    assert type(request).from_bytes(bytes(request)).uuid == value


def test_a_python_keyword_member_keeps_the_dsl_underscore():
    assert "pass_" in proto.BiomeConsolidatedFeatureData.__match_args__


def test_decode_is_strict():
    packet = proto.PlayStatusPacket(status=proto.PlayStatus.PLAYER_SPAWN)
    with pytest.raises(ValueError, match="trailing bytes"):
        proto.decode(packet.ID, bytes(packet) + b"\x00")
    with pytest.raises(ValueError):
        proto.decode(packet.ID, bytes(packet)[:-1])
    with pytest.raises(KeyError):
        proto.decode(1023, b"")


def test_every_packet_class_is_registered_under_its_id():
    for packet_id, cls in proto.PACKETS.items():
        assert cls.ID == packet_id


def test_an_empty_list_keeps_its_element_type_through_a_round_trip():
    from bedrock_protocol._native.nbt import ListTag

    wire = bytes.fromhex("0000000a000901610a0000")
    packet = proto.BlockActorDataPacket.from_bytes(wire)
    assert packet.data["a"].type == 10
    assert len(packet.data["a"]) == 0
    assert bytes(packet) == wire

    built = proto.BlockActorDataPacket(data=type(packet.data)({"a": ListTag(type=10)}))
    assert bytes(built) == wire
    assert ListTag(type=10) != ListTag()
    with pytest.raises(ValueError):
        ListTag(type=12)
