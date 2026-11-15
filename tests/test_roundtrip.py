import importlib

import pytest

import bedrock_protocol

versions = [importlib.import_module(f"bedrock_protocol.v{version}") for version in bedrock_protocol.versions]

packets = [(m, cls) for m in versions for cls in m.packets.values()]


def label_paths(scope, prefix, known):
    for name in dir(scope):
        member = getattr(scope, name)
        if not name.startswith("_") and isinstance(member, type):
            if member in known:
                yield member, f"{prefix}.{name}"
            yield from label_paths(member, f"{prefix}.{name}", known)


SERIALIZABLE = {}
for module in versions:
    for cls, path in label_paths(module, module.__name__, module.modes):
        for mode, since in module.modes[cls].items():
            SERIALIZABLE.setdefault((cls, mode, since), (module, cls, mode, path))


BINDING_GAP = {f"{version.__name__}.CommandRequestPacket" for version in versions} | {
    "bedrock_protocol.v729.SerializedPersonaPieceHandle",
    "bedrock_protocol.v729.TintMapColor",
}
GAP = pytest.mark.xfail(
    raises=bedrock_protocol.EncodeError,
    strict=True,
    reason="binding gap: a name-coded enum defaults to an unnamed value",
)


def packet_id(value):
    return value.__name__.rsplit(".", 1)[-1] if hasattr(value, "__name__") else str(value)


def gap(path):
    return GAP if path in BINDING_GAP else ()


VALUES = [
    pytest.param(
        module,
        cls,
        mode,
        marks=gap(path),
        id=path if mode == bedrock_protocol.SerializationMode.DEFAULT else f"{path}-{mode.name.lower()}",
    )
    for module, cls, mode, path in SERIALIZABLE.values()
]


@pytest.mark.parametrize(
    ("module", "cls"),
    [pytest.param(m, cls, marks=gap(f"{m.__name__}.{cls.__qualname__}")) for m, cls in packets],
    ids=packet_id,
)
def test_a_default_packet_round_trips_through_its_framed_header(module, cls):
    packet = cls()
    header, framed = module.decode_packet(module.encode_packet(packet))
    assert (header.packet_id, header.recipient_sub_id, header.sender_sub_id) == (cls.ID, 0, 0)
    assert framed == packet


@pytest.mark.parametrize(("module", "cls", "mode"), VALUES)
def test_a_default_value_decodes_to_itself(module, cls, mode):
    value = cls()
    assert module.decode(cls, module.encode(value, mode=mode), mode=mode) == value


@pytest.mark.parametrize(("module", "cls", "mode"), VALUES)
def test_a_default_value_encodes_again_to_the_same_bytes(module, cls, mode):
    data = module.encode(cls(), mode=mode)
    assert module.encode(module.decode(cls, data, mode=mode), mode=mode) == data
