"""Every bound class must survive its own codec unchanged.

A default-constructed value is the one input every class has, so each packet and
each serializable struct is written, read back and compared, both as a value and
as bytes, through the class methods and through the version's dispatch by id.
"""

import enum

import pytest
from conftest import VERSIONS


def _classes(scope, seen):
    for name in dir(scope):
        if name.startswith("_"):
            continue
        cls = getattr(scope, name)
        if isinstance(cls, type) and cls not in seen and cls.__module__.startswith("bedrock_protocol"):
            seen.add(cls)
            yield cls
            yield from _classes(cls, seen)


PACKETS = [(m, cls) for m in VERSIONS for cls in m.PACKETS.values()]
SERIALIZABLE = [
    cls
    for m in VERSIONS
    for scope in (m, m.legacy)
    for cls in _classes(scope, set())
    if hasattr(cls, "from_bytes") and not issubclass(cls, enum.Enum)
]


def _holds_unnamed_enum(value):
    """Whether any member, at any depth, is an enum value the schema does not name.
    Such a default is not a valid value: a name-coded enum has nothing to write for it."""
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


def _id(value):
    return value.__name__.rsplit(".", 1)[-1] if hasattr(value, "__name__") else str(value)


def test_every_version_binds_packets():
    assert VERSIONS
    for m in VERSIONS:
        assert len(m.PACKETS) > 200, m.__name__


@pytest.mark.parametrize(("module", "cls"), PACKETS, ids=_id)
def test_a_default_packet_round_trips(module, cls):
    packet = cls()
    body = module.encode(packet)
    assert body == bytes(packet)

    try:
        back = module.decode(cls.ID, body)
    except ValueError:
        assert _holds_unnamed_enum(packet)
        return
    assert type(back) is cls
    assert back == packet
    assert module.encode(back) == body

    header, framed = module.decode_packet(module.encode_packet(packet))
    assert (header.packet_id, header.recipient_sub_id, header.sender_sub_id) == (cls.ID, 0, 0)
    assert framed == packet


@pytest.mark.parametrize("cls", SERIALIZABLE, ids=lambda cls: f"{cls.__module__}.{cls.__qualname__}")
def test_a_default_value_round_trips(cls):
    value = cls()
    data = bytes(value)
    try:
        back = cls.from_bytes(data)
    except ValueError:
        assert _holds_unnamed_enum(value)
        return
    assert back == value
    assert bytes(back) == data
