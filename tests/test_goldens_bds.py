import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "goldens" / "bds.py"


@pytest.fixture(scope="module")
def bds():
    spec = importlib.util.spec_from_file_location("goldens_bds", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gap(bds, shown, value, enums=None):
    return bds.missing([scalar for _, scalar in bds.leaves(shown)], bds.leaves(value), enums)


def test_an_enum_the_case_names_matches_the_number_bds_shows(bds):
    assert gap(bds, {"Status": 1}, {"status": "LOGIN_FAILED_CLIENT_OLD"}, {"status": 1}) is None


def test_an_enum_the_case_names_does_not_match_another_number(bds):
    value = {"status": "LOGIN_FAILED_CLIENT_OLD"}
    assert gap(bds, {"Status": 99}, value, {"status": 1}) == ("status", "LOGIN_FAILED_CLIENT_OLD")


def test_an_enum_leaf_the_case_gives_no_number_for_does_not_match(bds):
    value = {"status": "LOGIN_FAILED_CLIENT_OLD"}
    assert gap(bds, {"Status": 1}, value) == ("status", "LOGIN_FAILED_CLIENT_OLD")


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
    shown = [json.loads(scalar) for scalar in bds.SCALAR.findall(text)]
    return bds.missing(shown, bds.leaves(value))


def test_scalars_scanned_from_text_that_is_not_json_hold_the_values(bds):
    text = '{"Data":10,"":1,"b":{"data":7},7:"bytes",3:1,254:3,{"data":2.5}:5,"str":{"data":"text"},0}'
    value = {"b": {"ByteTag": 7}, "bytes": {"ByteArrayTag": [1, -2, 3]}, "str": {"StringTag": "text"}}
    assert scanned(bds, text, value) is None


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


@pytest.fixture(scope="module")
def values():
    pytest.importorskip("bedrock_protocol_compiler")
    spec = importlib.util.spec_from_file_location("goldens_values", SCRIPT.with_name("values.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_an_enum_leaf_is_numbered_by_its_key_path(values):
    from bedrock_protocol import v2168

    value = {"status": "LOGIN_FAILED_CLIENT_OLD"}
    assert values.enum_numbers(v2168.packets[2].from_json(value), value) == {"status": 1}


def test_an_enum_inside_a_variant_alternative_is_numbered(values):
    from bedrock_protocol import v2168

    value = {
        "localize": False,
        "body": {"MessageOnly": {"type": "TRANSLATE", "message": "s3"}},
        "xuid": "s4",
        "platform_id": "s5",
        "filtered_message": "s6",
    }
    packet = v2168.packets[9].from_json(value)
    assert values.enum_numbers(packet, value) == {"body.MessageOnly.type": int(packet.body.type)}


@pytest.fixture(scope="module")
def schema(values):
    return values.Schema(values.build(values.PROTOCOL_DIR))


def generated(values, schema, name):
    return values.values_of(schema, 2168, next(each for each in schema.order if each.name == name))[0]


@pytest.mark.parametrize(
    ("name", "field", "bound"),
    [
        ("PlayerVideoCapturePacket", "stop_video_capture", "start_video_capture"),
        ("ClientboundUpdateSoundDataPacket", "resume", "stop"),
        ("CylinderDataPayload", "radius_z", "radius_x"),
    ],
    ids=["video-capture", "sound-data", "cylinder"],
)
def test_a_name_bds_binds_to_another_names_member_repeats_its_value(values, schema, name, field, bound):
    chosen = generated(values, schema, name)
    assert [each[field] for each in chosen] == [each[bound] for each in chosen]


@pytest.mark.parametrize(
    ("name", "field", "gate", "member"),
    [
        ("ItemStackResponseInfo", "containers", "result", "SUCCESS"),
        ("UniqueId", "key_entity_id", "type", "ENTITY"),
        ("UniqueId", "key_block_pos", "type", "BLOCK_ENTITY"),
    ],
    ids=["containers", "entity-id", "block-pos"],
)
def test_an_optional_bds_derives_from_an_enum_is_present_exactly_for_its_member(
    values, schema, name, field, gate, member
):
    chosen = generated(values, schema, name)
    assert {(each[gate] == member, each[field] is not None) for each in chosen} == {(True, True), (False, False)}


@pytest.mark.parametrize(
    ("name", "field", "kept"),
    [
        ("ContentIdentity", "identity", "11111111-2222-4333-8444-555555555555"),
        ("PackInstanceId", "pack_id", "22222222-3333-4444-8555-666666666666"),
        ("AttributeModifier", "id", "33333333-4444-4555-8666-777777777777"),
        ("SemVersion", "version", "1.2.3"),
        ("PackInstanceId", "version", "2.3.4"),
        ("ResourcePackStackPacket", "base_game_version", "1.21.0"),
    ],
    ids=["content-identity", "pack-id", "modifier-id", "sem-version", "pack-version", "base-game-version"],
)
def test_a_leaf_bds_normalises_is_generated_as_a_value_bds_keeps(values, schema, name, field, kept):
    chosen = generated(values, schema, name)
    assert [each[field] for each in chosen] == [kept for _ in chosen]
