import json
import re

FLAT = re.compile(r'\[\n((?: +(?:"(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null),?\n)+) *\]')


def layout(cases):
    return (
        FLAT.sub(
            lambda m: "[" + ", ".join(line.strip() for line in m[1].rstrip("\n").split(",\n")) + "]",
            json.dumps(cases, indent=1),
        )
        + "\n"
    )


def test_a_case_value_encodes_to_its_bytes(cls, case):
    assert bytes(cls.from_json(case["value"])).hex() == case["bytes"]


def test_a_case_bytes_decode_to_its_value(cls, case):
    assert json.dumps(cls.from_bytes(bytes.fromhex(case["bytes"])).to_json()) == json.dumps(case["value"])


def test_a_case_file_puts_each_flat_list_on_one_line(case_file):
    assert case_file.read_text() == layout(json.loads(case_file.read_text()))
