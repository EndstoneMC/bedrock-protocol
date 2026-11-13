import pytest

from bedrock_protocol_compiler.builder import build
from bedrock_protocol_compiler.descriptor import Package

INIT = """
from bedrock_protocol_compiler.dsl import (
    array, auto, bitset, builtin, double, field, int8, int16, int32, int64, packet, sentinel, type, uint8, uint16,
    uint32,
    uint64, uvarint32, uvarint64, value, varint32, varint64
)

versions = (1, 2, 3, 4, 5)

releases = {1: "1.1.0", 2: "1.2.0", 3: "1.3.0", 4: "1.4.0", 5: "1.5.x"}
"""


@pytest.fixture
def build_package(tmp_path):
    def build_modules(modules: dict[str, str], init: str = INIT) -> Package:
        package_dir = tmp_path / "protocol"
        package_dir.mkdir()
        (package_dir / "__init__.py").write_text(init)
        for stem, source in modules.items():
            (package_dir / f"{stem}.py").write_text(source)
        return build(package_dir)

    return build_modules
