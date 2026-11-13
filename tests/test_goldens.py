import json
import re

FLAT = re.compile(
    r'([\[{])\n((?: +(?:"(?:[^"\\]|\\.)*": )?'
    r'(?:"(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null),?\n)+) *([\]}])'
)


def layout(cases):
    return (
        FLAT.sub(
            lambda m: m[1] + ", ".join(line.strip() for line in m[2].rstrip("\n").split(",\n")) + m[3],
            json.dumps(cases, indent=1),
        )
        + "\n"
    )


def test_a_case_value_encodes_to_its_bytes(cls, case):
    assert bytes(cls.from_json(case["value"])).hex() == case["bytes"]


def test_a_case_bytes_decode_to_its_value(cls, case):
    assert json.dumps(cls.from_bytes(bytes.fromhex(case["bytes"])).to_json()) == json.dumps(case["value"])


def test_a_case_file_puts_each_flat_list_and_object_on_one_line(case_file):
    assert case_file.read_text() == layout(json.loads(case_file.read_text()))
