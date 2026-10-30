import re
from pathlib import Path

import pytest


def varuint(value):
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


@pytest.fixture
def golden():
    def load(packet_id, filename, variable="golden", occurrence=0):
        source = (Path(__file__).parents[1] / filename).read_text(encoding="utf-8")
        pattern = rf"const std::string {variable}\s*=\s*bytes\(\{{(.*?)\}}\);"
        found = re.findall(pattern, source, re.S)
        assert len(found) > occurrence, (filename, variable, occurrence)
        body = bytes(int(value, 16) for value in re.findall(r"0x([0-9a-fA-F]{2})", found[occurrence]))
        return varuint(packet_id) + body

    return load
