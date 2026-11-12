import json


def test_a_case_value_encodes_to_its_bytes(cls, case):
    assert bytes(cls.from_json(case["value"])).hex() == case["bytes"]


def test_a_case_bytes_decode_to_its_value(cls, case):
    assert json.dumps(cls.from_bytes(bytes.fromhex(case["bytes"])).to_json()) == json.dumps(case["value"])


def test_a_case_file_holds_a_case(cases):
    assert cases
