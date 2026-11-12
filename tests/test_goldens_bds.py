import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "goldens" / "bds.py"


@pytest.fixture(scope="module")
def bds():
    spec = importlib.util.spec_from_file_location("goldens_bds", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gap(bds, shown, value):
    return bds.missing([scalar for _, scalar in bds.leaves(shown)], bds.leaves(value))


def test_an_enum_the_case_names_matches_the_number_bds_shows(bds):
    assert gap(bds, {"Status": 1}, {"status": "LOGIN_FAILED_CLIENT_OLD"}) is None


def test_a_string_that_is_no_enum_name_does_not_match_a_number(bds):
    assert gap(bds, {"Type": 4}, {"value": "s35"}) == ("value", "s35")


def test_a_leaf_bds_adds_is_skipped(bds):
    shown = {"Response": {"Response Type": "downloading", "Downloading Packs": ["s1"]}}
    assert gap(bds, shown, {"response": {"Downloading": {"downloading_packs": ["s1"]}}}) is None


def test_a_value_bds_shows_otherwise_is_reported_by_its_case_path(bds):
    assert gap(bds, {"X": 1, "Y": 2}, {"pos": {"x": 1, "y": 3}}) == ("pos.y", 3)


def test_a_bool_does_not_match_a_number(bds):
    assert gap(bds, {"Flag": 1}, {"flag": True}) == ("flag", True)


def test_a_whole_number_matches_the_float_bds_shows(bds):
    assert gap(bds, {"Value": 2.0}, {"value": 2}) is None


def test_a_null_in_the_case_needs_nothing_from_bds(bds):
    assert gap(bds, {"Tick": 5}, {"tags": None, "tick": 5}) is None


def scanned(bds, text, value):
    shown = [bds.json.loads(scalar) for scalar in bds.SCALAR.findall(text)]
    return bds.missing(shown, bds.leaves(value))


def test_scalars_scanned_from_text_that_is_not_json_hold_the_values(bds):
    text = '{"Data":10,"":1,"b":{"data":7},7:"bytes",3:1,254:3,{"data":2.5}:5,"str":{"data":"text"},0}'
    value = {"str": {"StringTag": "text"}, "b": {"ByteTag": 7}, "bytes": {"ByteArrayTag": [1, -2, 3]}}
    assert scanned(bds, text, value) is None


def test_a_compound_is_compared_with_its_keys_sorted(bds):
    text = '{"a":{"data":1},"b":{"data":2}}'
    assert scanned(bds, text, {"b": {"IntTag": 2}, "a": {"IntTag": 1}}) is None


def test_scanned_text_that_lacks_a_value_is_reported(bds):
    assert scanned(bds, '{"b":{"data":7}}', {"i": {"IntTag": 70000}}) == ("i.IntTag", 70000)


def test_scanned_text_holds_a_repeated_value_once_per_appearance(bds):
    assert scanned(bds, '{"a":7}', {"x": 7, "y": 7}) == ("y", 7)


@pytest.mark.parametrize("name", ["clientcanceled", "client_canceled"])
def test_an_enum_matches_the_lower_case_name_bds_shows(bds, name):
    assert gap(bds, {"Reason": name}, {"reason": "CLIENT_CANCELED"}) is None


def test_a_signed_integer_matches_the_unsigned_one_bds_shows(bds):
    assert gap(bds, {"Rotation X": 213}, {"rot_x": -43}) is None


def test_integers_that_differ_in_value_do_not_match(bds):
    assert gap(bds, {"Rotation X": 212}, {"rot_x": -43}) == ("rot_x", -43)


def test_a_uuid_matches_the_two_halves_bds_shows(bds):
    shown = {"UUID": {"Most Significant Bits": 0, "Least Significant Bits": 2}}
    assert gap(bds, shown, {"uuid": "00000000-0000-0000-0000-000000000002"}) is None


def test_a_blob_in_hex_matches_the_characters_bds_shows(bds):
    assert gap(bds, {"Chunk Data": "\u0004\u0001\u0002"}, {"data": "040102"}) is None
