import json
import re

from cereal import load, save

LOWER_WITH_UNDER = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")
FLAT = re.compile(r'\[\n((?: +(?:"(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null),?\n)+) *\]')


def layout(cases):
    return (
        FLAT.sub(
            lambda m: "[" + ", ".join(line.strip() for line in m[1].rstrip("\n").split(",\n")) + "]",
            json.dumps(cases, indent=1),
        )
        + "\n"
    )


def test_a_case_value_encodes_to_its_bytes(cls, round_trip):
    assert bytes(load(cls, round_trip["value"])).hex() == round_trip["bytes"]


def test_a_case_bytes_decode_to_its_value(cls, case):
    assert json.dumps(save(cls.from_bytes(bytes.fromhex(case["bytes"])))) == json.dumps(case["value"])


def test_a_case_file_names_each_case_once_in_lower_with_under(case_file):
    names = [case["id"] for case in json.loads(case_file.read_text())]
    assert all(LOWER_WITH_UNDER.fullmatch(name) for name in names)
    assert len(set(names)) == len(names)


def test_a_case_file_puts_each_flat_list_on_one_line(case_file):
    assert case_file.read_text() == layout(json.loads(case_file.read_text()))
