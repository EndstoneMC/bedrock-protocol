"""Executed explicitly by run.py against its freshly built native fixture."""

import importlib
import os
from pathlib import Path

import pytest

from bedrock_protocol import MapView, SequenceView, _native


def native_type(name):
    return next(value for value in vars(_native._types).values() if getattr(value, "__name__", None) == name)


def test_native_identity():
    assert Path(_native.__file__).resolve().parent == Path(os.environ["BPC_NATIVE_FIXTURE_PACKAGE"]).resolve()


def test_alias_module_imports_native_container_types():
    module = importlib.import_module("bedrock_protocol.v1001")
    assert module.Children is SequenceView
    assert module.ChildMap is MapView
    child = module.Child(value=7)
    value = module.Aliases(children=[child], by_name={"x": child})
    assert isinstance(value.children, module.Children)
    assert isinstance(value.by_name, module.ChildMap)
    assert type(value.children[0]) is type(value.by_name["x"]) is module.Child


@pytest.mark.parametrize("enabled,selected", [(False, False), (False, True), (True, False)])
def test_counted_condition_off(enabled, selected):
    cls = native_type("Counted")
    value = cls(enabled=enabled, selected=selected, count=1, values=None)
    assert value.values is None
    assert value.wire_bytes() == bytes([enabled, selected, 1])
    with pytest.raises(ValueError, match="must be None"):
        cls(enabled=enabled, selected=selected, count=1, values=[])


def test_counted_optional_absent():
    value = native_type("Counted")(enabled=True, selected=True, count=1, values=None)
    assert value.values is None
    assert value.wire_bytes() == b"\x01\x01\x01\x00"


@pytest.mark.parametrize("count,values,wire", [(0, [], b"\x01\x01\x00\x01"), (1, [7], b"\x01\x01\x01\x01\x07")])
def test_counted_matching(count, values, wire):
    value = native_type("Counted")(enabled=True, selected=True, count=count, values=values)
    assert list(value.values) == values
    assert value.wire_bytes() == wire


@pytest.mark.parametrize("count,values", [(1, []), (0, [7]), (2, [7])])
def test_counted_mismatch_rejected(count, values):
    with pytest.raises(ValueError, match="values length disagrees with its count"):
        native_type("Counted")(enabled=True, selected=True, count=count, values=values)


@pytest.mark.parametrize("view", [False, True], ids=["mapping", "map_view"])
@pytest.mark.parametrize("count", [255, 256])
def test_map_prefix_boundary(view, count):
    cls = native_type("NarrowMap")
    data = {f"{i:03}": i % 256 for i in range(count)}
    source = native_type("WideMap")(values=data).values if view else data
    assert len(source) == count
    if count == 256:
        with pytest.raises(ValueError, match="length prefix"):
            cls(values=source)
    else:
        value = cls(values=source)
        assert len(value.values) == count
        assert {key: value.values[key] for key in value.values} == data
        expected = b"\xff" + b"".join(b"\x03" + key.encode() + bytes([data[key]]) for key in sorted(data))
        assert value.wire_bytes() == expected
        assert type(value.values) is type(native_type("WideMap")(values={}).values)


def test_map_prefix_counts_distinct_emitted_keys():
    class RepeatedItems:
        def items(self):
            return [(f"{i % 255:03}", i % 256) for i in range(256)]

    value = native_type("NarrowMap")(values=RepeatedItems())
    assert len(value.values) == 255
    assert value.values["000"] == 255
    assert value.wire_bytes()[0] == 255
