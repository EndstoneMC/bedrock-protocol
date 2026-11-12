import enum
import importlib

import pytest

import bedrock_protocol

VERSIONS = [importlib.import_module(f"bedrock_protocol.v{version}") for version in bedrock_protocol.VERSIONS]


def _classes(scope, seen):
    for name in dir(scope):
        if name.startswith("_"):
            continue
        cls = getattr(scope, name)
        if isinstance(cls, type) and cls not in seen and cls.__module__.startswith("bedrock_protocol"):
            seen.add(cls)
            yield cls
            yield from _classes(cls, seen)


def _holds_unnamed_enum(value):
    annotations = getattr(type(value), "__annotations__", {})
    for name in getattr(type(value), "__match_args__", ()):
        member = getattr(value, name)
        kind = annotations.get(name)
        if isinstance(kind, type) and issubclass(kind, enum.Enum) and not isinstance(member, kind):
            return True
        items = member if isinstance(member, list) else [member]
        if any(_holds_unnamed_enum(item) for item in items):
            return True
    return False


def _decodes(decode, data):
    try:
        decode(data)
    except ValueError:
        return False
    return True


PACKETS = [(m, cls) for m in VERSIONS for cls in m.PACKETS.values()]
ROUND_TRIPPING_PACKETS = [(m, cls) for m, cls in PACKETS if _decodes(cls.from_bytes, bytes(cls()))]
UNDECODABLE_PACKETS = [(m, cls) for m, cls in PACKETS if (m, cls) not in ROUND_TRIPPING_PACKETS]
SERIALIZABLE = list(
    dict.fromkeys(
        cls
        for scope in (bedrock_protocol, *VERSIONS, *(m.pre_cereal for m in VERSIONS))
        for cls in _classes(scope, set())
        if hasattr(cls, "from_bytes") and not issubclass(cls, enum.Enum)
    )
)
ROUND_TRIPPING_VALUES = [cls for cls in SERIALIZABLE if _decodes(cls.from_bytes, bytes(cls()))]
UNDECODABLE_VALUES = [cls for cls in SERIALIZABLE if cls not in ROUND_TRIPPING_VALUES]


def packet_id(value):
    return value.__name__.rsplit(".", 1)[-1] if hasattr(value, "__name__") else str(value)


def value_id(cls):
    return f"{cls.__module__}.{cls.__qualname__}"


def test_every_version_binds_packets(protocol):
    assert len(protocol.PACKETS) > 200


@pytest.mark.parametrize(("module", "cls"), ROUND_TRIPPING_PACKETS, ids=packet_id)
def test_a_default_packet_round_trips_through_its_framed_header(module, cls):
    packet = cls()
    header, framed = module.decode_packet(module.encode_packet(packet))
    assert (header.packet_id, header.recipient_sub_id, header.sender_sub_id) == (cls.ID, 0, 0)
    assert framed == packet


@pytest.mark.parametrize("cls", ROUND_TRIPPING_VALUES, ids=value_id)
def test_a_default_value_decodes_to_itself(cls):
    value = cls()
    assert cls.from_bytes(bytes(value)) == value


@pytest.mark.parametrize("cls", ROUND_TRIPPING_VALUES, ids=value_id)
def test_a_default_value_encodes_again_to_the_same_bytes(cls):
    data = bytes(cls())
    assert bytes(cls.from_bytes(data)) == data


@pytest.mark.parametrize("cls", UNDECODABLE_VALUES, ids=value_id)
def test_a_default_value_holding_an_unnamed_enum_is_rejected_on_decode(cls):
    with pytest.raises(ValueError, match="at byte"):
        cls.from_bytes(bytes(cls()))


@pytest.mark.parametrize("cls", [cls for _, cls in UNDECODABLE_PACKETS], ids=value_id)
def test_only_a_default_packet_holding_an_unnamed_enum_is_rejected_on_decode(cls):
    assert _holds_unnamed_enum(cls())


@pytest.mark.parametrize("cls", UNDECODABLE_VALUES, ids=value_id)
def test_only_a_default_value_holding_an_unnamed_enum_is_rejected_on_decode(cls):
    assert _holds_unnamed_enum(cls())
