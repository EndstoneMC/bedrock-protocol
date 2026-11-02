import importlib

import pytest

from bedrock_protocol import _native

#: Every protocol version this build of the extension binds, as its Python module.
VERSIONS = [
    importlib.import_module(f"bedrock_protocol.{name}")
    for name in sorted(dir(_native))
    if name.startswith("v") and name[1:].isdigit()
]


@pytest.fixture(params=VERSIONS, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def protocol(request):
    return request.param
