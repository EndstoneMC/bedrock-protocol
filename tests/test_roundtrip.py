import enum
import importlib

import pytest

import bedrock_protocol

versions = [importlib.import_module(f"bedrock_protocol.v{version}") for version in bedrock_protocol.versions]


def _classes(scope, seen):
    for name in dir(scope):
        if name.startswith("_"):
            continue
        cls = getattr(scope, name)
        if isinstance(cls, type) and cls not in seen and cls.__module__.startswith("bedrock_protocol"):
            seen.add(cls)
            yield cls
            yield from _classes(cls, seen)


packets = [(m, cls) for m in versions for cls in m.packets.values()]
SERIALIZABLE = list(
    dict.fromkeys(
        cls
        for scope in (bedrock_protocol, *versions, *(m.pre_cereal for m in versions))
        for cls in _classes(scope, set())
        if hasattr(cls, "from_bytes") and not issubclass(cls, enum.Enum)
    )
)


BINDING_GAP = {
    f"bedrock_protocol.v{version}.CommandRequestPacket" for version in (776, 800, 859, 944, 975, 1001, 2168, 2193, 2225)
} | {"bedrock_protocol.v2225.pre_cereal.SerializedPersonaPieceHandle", "bedrock_protocol.v2225.pre_cereal.TintMapColor"}
GAP = pytest.mark.xfail(
    raises=bedrock_protocol.DecodeError,
    strict=True,
    reason="binding gap: a name-coded enum defaults to an unnamed value",
)


def packet_id(value):
    return value.__name__.rsplit(".", 1)[-1] if hasattr(value, "__name__") else str(value)


def value_id(cls):
    return f"{cls.__module__}.{cls.__qualname__}"


def gap(cls):
    return GAP if value_id(cls) in BINDING_GAP else ()


VALUES = [pytest.param(cls, marks=gap(cls)) for cls in SERIALIZABLE]


@pytest.mark.parametrize(("module", "cls"), [pytest.param(m, cls, marks=gap(cls)) for m, cls in packets], ids=packet_id)
def test_a_default_packet_round_trips_through_its_framed_header(module, cls):
    packet = cls()
    header, framed = module.decode_packet(module.encode_packet(packet))
    assert (header.packet_id, header.recipient_sub_id, header.sender_sub_id) == (cls.ID, 0, 0)
    assert framed == packet


@pytest.mark.parametrize("cls", VALUES, ids=value_id)
def test_a_default_value_decodes_to_itself(cls):
    value = cls()
    assert cls.from_bytes(bytes(value)) == value


@pytest.mark.parametrize("cls", VALUES, ids=value_id)
def test_a_default_value_encodes_again_to_the_same_bytes(cls):
    data = bytes(cls())
    assert bytes(cls.from_bytes(data)) == data
