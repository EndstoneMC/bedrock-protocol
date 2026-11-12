import re
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_the_umbrella_header_names_exactly_the_module_headers_and_packets_h():
    stems = {path.stem for path in (ROOT / "protocol").glob("*.py") if path.stem != "__init__"}
    umbrella = (ROOT / "include/bedrock/protocol.hpp").read_text()

    assert set(re.findall(r'#include "bedrock/protocol/(\w+)\.h"', umbrella)) == stems | {"packets"}
