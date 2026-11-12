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


def gap(bds, shown, value, enums=None, printed=None):
    return bds.missing([scalar for _, scalar in bds.leaves(shown)], bds.leaves(value), enums, printed)


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


def test_an_upper_case_string_that_is_no_enum_does_not_match_its_lower_case(bds):
    assert gap(bds, {"Name": "abc"}, {"name": "ABC"}) == ("name", "ABC")


def test_a_leaf_bds_adds_is_skipped(bds):
    shown = {"Response": {"Response Type": "downloading", "Downloading Packs": ["s1"]}}
    assert gap(bds, shown, {"response": {"Downloading": {"downloading_packs": ["s1"]}}}) is None


def test_a_value_bds_shows_otherwise_is_reported_by_its_case_path(bds):
    assert gap(bds, {"X": 1, "Y": 2}, {"pos": {"x": 1, "y": 3}}) == ("pos.y", 3)


def test_a_bool_does_not_match_a_number(bds):
    assert gap(bds, {"Flag": 1}, {"flag": True}) == ("flag", True)


def test_a_whole_number_does_not_match_the_float_bds_shows(bds):
    assert gap(bds, {"Value": 2.0}, {"value": 2}) == ("value", 2)


def test_a_float_matches_the_same_float_bds_shows(bds):
    assert gap(bds, {"Value": 2.0}, {"value": 2.0}) is None


def test_a_null_in_the_case_needs_nothing_from_bds(bds):
    assert gap(bds, {"Tick": 5}, {"tags": None, "tick": 5}) is None


def scanned(bds, text, value):
    shown = [json.loads(scalar) for scalar in bds.SCALAR.findall(text)]
    return bds.missing(shown, bds.leaves(value))


def test_scalars_scanned_from_text_that_is_not_json_hold_the_values(bds):
    text = '{"Data":10,"":1,"b":{"data":7},7:"bytes",3:1,2:3,{"data":2.5}:5,"str":{"data":"text"},0}'
    value = {"b": {"ByteTag": 7}, "bytes": {"ByteArrayTag": [1, 2, 3]}, "str": {"StringTag": "text"}}
    assert scanned(bds, text, value) is None


def test_a_byte_bds_prints_unsigned_does_not_match_the_signed_byte_of_the_case(bds):
    text = '{"Data":10,"":1,7:"bytes",3:1,254:3,0}'
    assert scanned(bds, text, {"bytes": {"ByteArrayTag": [1, -2, 3]}}) == ("bytes.ByteArrayTag[1]", -2)


def test_scanned_text_that_lacks_a_value_is_reported(bds):
    assert scanned(bds, '{"b":{"data":7}}', {"i": {"IntTag": 70000}}) == ("i.IntTag", 70000)


def test_scanned_text_holds_a_repeated_value_once_per_appearance(bds):
    assert scanned(bds, '{"a":7}', {"x": 7, "y": 7}) == ("y", 7)


def test_a_name_coded_enum_matches_the_wire_name_bds_shows(bds):
    shown = {"Reason": "clientcanceled"}
    assert gap(bds, shown, {"reason": "CLIENT_CANCELED"}, {"reason": 2}, {"reason": "clientcanceled"}) is None


def test_a_name_coded_enum_does_not_match_another_spelling_of_its_name(bds):
    shown = {"Reason": "client_canceled"}
    value = {"reason": "CLIENT_CANCELED"}
    assert gap(bds, shown, value, {"reason": 2}, {"reason": "clientcanceled"}) == ("reason", "clientcanceled")


def test_a_name_coded_enum_does_not_match_its_number(bds):
    shown = {"Reason": 2}
    value = {"reason": "CLIENT_CANCELED"}
    assert gap(bds, shown, value, {"reason": 2}, {"reason": "clientcanceled"}) == ("reason", "clientcanceled")


def test_an_integer_matches_the_number_its_wire_type_prints(bds):
    assert gap(bds, {"Rotation X": 213}, {"rot_x": -43}, printed={"rot_x": 213}) is None


def test_an_integer_does_not_match_its_bits_at_another_signedness(bds):
    assert gap(bds, {"Rotation X": 213}, {"rot_x": -43}) == ("rot_x", -43)


def test_integers_that_differ_in_value_do_not_match(bds):
    assert gap(bds, {"Rotation X": 212}, {"rot_x": -43}) == ("rot_x", -43)


def test_a_uuid_matches_the_two_halves_bds_shows(bds):
    shown = {"UUID": {"Most Significant Bits": 0, "Least Significant Bits": 2}}
    assert gap(bds, shown, {"uuid": "00000000-0000-0000-0000-000000000002"}) is None


def test_a_blob_in_hex_matches_the_characters_bds_shows(bds):
    assert gap(bds, {"Chunk Data": "\u0004\u0001\u0002"}, {"data": "040102"}) is None


def test_a_blob_byte_past_0x7f_matches_the_raw_byte_bds_writes(bds):
    assert gap(bds, {"Chunk Data": "\udc80\u0001\u0002"}, {"data": "800102"}) is None


def test_a_blob_byte_past_0x7f_does_not_match_its_latin_1_character(bds):
    assert gap(bds, {"Chunk Data": "\u0080\u0001\u0002"}, {"data": "800102"}) == ("data", "800102")


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
        ("StartGamePacket", "template_content_identity", "44444444-5555-4666-8777-888888888888"),
        ("SemVersion", "version", "1.2.3"),
        ("PackInstanceId", "version", "2.3.4"),
        ("ResourcePackStackPacket", "base_game_version", "1.21.0"),
        ("LevelSettings", "base_game_version", "1.21.0"),
        ("ExperimentToggle", "name", "gametest"),
        ("ExperimentToggle", "enabled", True),
        ("Experiments", "experiments_ever_toggled", True),
        (
            "SubClientLoginPacket",
            "connection_request",
            "250000007b2241757468656e7469636174696f6e54797065223a2d312c22546f6b656e223a22227d0a00000000",
        ),
        ("AgentActionEventPacket", "response", "null\n"),
        ("Color255RGBA", "a", 128),
        ("SerializableCells", "storage", [1, 2, 3, 4, 5, 6]),
        ("EffectDuration", "value", 600),
        ("NetworkStackLatencyPacket", "create_time", 0),
    ],
    ids=[
        "content-identity",
        "pack-id",
        "modifier-id",
        "template-content-identity",
        "sem-version",
        "pack-version",
        "base-game-version",
        "level-base-game-version",
        "experiment-name",
        "experiment-enabled",
        "experiments-ever-toggled",
        "sub-client-connection-request",
        "agent-response",
        "color-alpha",
        "cell-storage",
        "effect-duration",
        "latency-create-time",
    ],
)
def test_a_leaf_bds_normalises_is_generated_as_a_value_bds_keeps(values, schema, name, field, kept):
    chosen = generated(values, schema, name)
    assert [each[field] for each in chosen] == [kept for _ in chosen]


def test_level_settings_carry_the_game_rules_bds_writes_in_its_order(values, schema):
    rules = generated(values, schema, "LevelSettings")[0]["game_rules"]["rules"]
    assert (len(rules), rules[0]["name"], rules[-1]["name"]) == (39, "commandBlockOutput", "tntExplosionDropDecay")


@pytest.mark.parametrize(
    ("name", "value", "printed"),
    [
        ("MoveActorAbsolutePacket", {"move_data": {"rot_x": -43, "rot_y": 5}}, {"move_data.rot_x": 213}),
        ("ResourcePackDataInfoPacket", {"chunk_size": 7, "nb_chunks": -593}, {"nb_chunks": 4294966703}),
        ("SetTimePacket", {"time": -5}, {}),
    ],
    ids=["int8-as-uint8", "int32-as-uint32", "same-signedness"],
)
def test_an_integer_leaf_is_printed_at_its_wire_type(values, schema, name, value, printed):
    family = next(each for each in schema.order if each.name == name)
    assert values.Generator(schema, 2168).printed(values.StructRef(family), value) == printed


def test_an_enum_count_sentinel_is_never_generated(values, schema):
    options = generated(values, schema, "InventoryOptions")
    assert "COUNT" not in [each["layout_inv"] for each in options]


@pytest.mark.parametrize(
    ("name", "field", "read"),
    [
        ("SerializedNetworkItemStackDescriptor", "stack_size", 3),
        ("SerializedNetworkItemInstanceDescriptor", "stack_size", 4),
        ("NetworkItemInstanceDescriptorData", "stack_size", 5),
        ("SerializedRecipeIngredient", "stack_size", 2),
        ("SerializedRecipeIngredient", "aux_value", 6),
        ("ItemNameDescriptorData", "aux_value", 7),
        ("TakeActionData", "amount", 2),
        ("BeaconPaymentActionData", "secondary_effect_id", 10),
        ("CraftRepairAndDisenchantActionData", "repair_cost", 5),
        ("LevelChunkPacket", "sub_chunks_count", 4),
        ("CameraAimAssistPacket", "distance", 8.0),
        ("CameraSplineProgressKeyFrame", "alpha", 0.5),
        ("SkinImage", "width", 64),
        ("ItemStackRequestId", "raw_id", -5),
    ],
    ids=[
        "stack-size",
        "instance-stack-size",
        "request-stack-size",
        "ingredient-stack-size",
        "ingredient-aux",
        "name-aux",
        "take-amount",
        "beacon-effect",
        "repair-cost",
        "sub-chunks",
        "aim-distance",
        "spline-progress",
        "skin-width",
        "request-id",
    ],
)
def test_a_leaf_bds_reads_only_within_a_limit_is_generated_inside_it(values, schema, name, field, read):
    chosen = generated(values, schema, name)
    assert [each[field] for each in chosen] == [read for _ in chosen]


def test_a_fixed_leaf_behind_a_false_condition_keeps_its_default(values, schema):
    family = next(each for each in schema.order if each.name == "SerializedNetworkItemInstanceDescriptor")
    version = max(each for each in schema.versions if each < 2168)
    chosen = values.values_of(schema, version, family)[0]
    assert {(each["id"] != 0, each["stack_size"]) for each in chosen} == {(True, 4), (False, 0)}


@pytest.mark.parametrize(
    ("name", "value", "printed"),
    [
        (
            "ServerboundDataDrivenScreenClosedPacket",
            {"close_reason": "CLIENT_CANCELED"},
            {"close_reason": "clientcanceled"},
        ),
        ("AnimatePacket", {"swing_source": "ATTACK"}, {"swing_source": "attack"}),
    ],
    ids=["dropped-separator", "optional"],
)
def test_a_name_coded_enum_leaf_is_printed_by_its_wire_name(values, schema, name, value, printed):
    family = next(each for each in schema.order if each.name == name)
    assert values.Generator(schema, 2168).printed(values.StructRef(family), value) == printed


@pytest.mark.parametrize(
    ("name", "number", "named"),
    [("MolangVersion", 13, "LATEST"), ("CurrentCmdVersion", 50, "LATEST"), ("GameType", 0, "SURVIVAL")],
    ids=["molang-version", "command-version", "game-type"],
)
def test_a_number_two_members_share_is_named_as_to_json_names_it(values, schema, name, number, named):
    family = next(each for each in schema.order if each.name == name)
    assert values.Generator(schema, 2168).named(family)[number] == named


@pytest.mark.parametrize(
    ("name", "field", "read"),
    [
        ("CameraAimAssistCategoryPriorities", "entity_default", 50),
        ("LevelChunkPacket", "client_request_sub_chunk_limit", 8),
    ],
    ids=["entity-default", "sub-chunk-limit"],
)
def test_an_optional_bds_reads_only_within_a_limit_is_absent_or_inside_it(values, schema, name, field, read):
    assert {each[field] for each in generated(values, schema, name)} == {read, None}


def test_a_map_value_bds_reads_only_within_a_limit_is_generated_inside_it(values, schema):
    chosen = generated(values, schema, "CameraAimAssistCategoryPriorities")
    assert {priority for each in chosen for priority in each["blocks"].values()} == {20}
