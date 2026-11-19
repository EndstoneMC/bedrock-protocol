import importlib

import pytest

import bedrock_protocol
from bedrock_protocol import _core
from bedrock_protocol._core import SerializationMode

versions = [importlib.import_module(f"bedrock_protocol.v{version}") for version in _core.modes]

packets = [(m, cls) for m in versions for cls in m.packets.values()]


SERIALIZABLE = {}
for module in versions:
    for cls, modes in _core.modes[module.VERSION].items():
        for mode, since in modes.items():
            SERIALIZABLE.setdefault((cls, mode, since), (module, cls, mode, f"{module.__name__}.{cls.__qualname__}"))


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
        id=path if mode == SerializationMode.DEFAULT else f"{path}-{mode.name.lower()}",
    )
    for module, cls, mode, path in SERIALIZABLE.values()
]


@pytest.mark.parametrize(
    ("module", "cls"),
    [pytest.param(m, cls, marks=gap(f"{m.__name__}.{cls.__qualname__}")) for m, cls in packets],
    ids=packet_id,
)
def test_a_default_packet_round_trips_at_every_protocol_that_has_it(module, cls):
    packet = cls()
    assert module.decode(cls, module.encode(packet)) == packet


@pytest.mark.parametrize(("module", "cls", "mode"), VALUES)
def test_a_default_value_decodes_to_itself(module, cls, mode):
    value = cls()
    data = _core.encode(module.VERSION, value, mode=mode)
    assert _core.decode(module.VERSION, cls, data, mode=mode) == value


@pytest.mark.parametrize(("module", "cls", "mode"), VALUES)
def test_a_default_value_encodes_again_to_the_same_bytes(module, cls, mode):
    data = _core.encode(module.VERSION, cls(), mode=mode)
    assert _core.encode(module.VERSION, _core.decode(module.VERSION, cls, data, mode=mode), mode=mode) == data
