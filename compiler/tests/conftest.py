import pytest

from bedrock_protocol_compiler.builder import build
from bedrock_protocol_compiler.descriptor import Package

INIT = """
from bedrock_protocol_compiler.dsl import builtin, double, field, int8, packet, type, uint8, uint32, uvarint32

versions = (1, 2, 3)
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
