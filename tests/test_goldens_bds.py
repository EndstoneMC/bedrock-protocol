import base64
import importlib.util
import json
import uuid
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "goldens" / "bds.py"


@pytest.fixture(scope="module")
def bds():
    spec = importlib.util.spec_from_file_location("goldens_bds", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_separator_rapidjson_does_not_write_there_is_refused(bds):
    with pytest.raises(ValueError, match="where rapidjson writes"):
        bds.tokens('{"a",1}')


def test_each_scalar_carries_the_bracket_and_index_that_hold_it(bds):
    text = '{"Data":10,"":1,"b":{"data":7},7:"bytes",3:1,254:3,0}'
    assert [(scalar, place[-1]) for scalar, place in bds.tokens(text)] == [
        ("Data", ("{", 0)),
        (10, ("{", 1)),
        ("", ("{", 2)),
        (1, ("{", 3)),
        ("b", ("{", 4)),
        ("data", ("{", 0)),
        (7, ("{", 1)),
        (7, ("{", 6)),
        ("bytes", ("{", 7)),
        (3, ("{", 8)),
        (1, ("{", 9)),
        (254, ("{", 10)),
        (3, ("{", 11)),
        (0, ("{", 12)),
    ]
    assert bds.tokens(text)[5][1] == (("[", 0), ("{", 5), ("{", 0))


def unmatched(bds, text, printed):
    return bds.unmatched(bds.tokens(text), printed)


def test_json_that_prints_each_listed_scalar_in_order_agrees(bds):
    assert unmatched(bds, '{"Status":1,"Player":{"Name":"s1"}}', [["status", 1], ["player.name", "s1"]]) is None


def test_a_scalar_bds_prints_that_the_list_lacks_is_reported(bds):
    text = '{"Response Type":"downloading","Downloading Packs":["s1"]}'
    found = unmatched(bds, text, [["downloading_packs[0]", "s1"]])
    assert found == "downloading_packs[0] is 's1' in the case and 'downloading' in BDS's JSON"


def test_a_listed_scalar_bds_does_not_print_is_reported(bds):
    assert unmatched(bds, '{"X":1}', [["x", 1], ["y", 2]]) == "y is 2 in the case and not in BDS's JSON"


def test_a_scalar_bds_prints_past_the_list_is_reported(bds):
    assert unmatched(bds, '{"X":1,"Y":2}', [["x", 1]]) == "BDS's JSON prints 2 past the case's last scalar"


def test_a_null_bds_prints_is_reported_unless_listed(bds):
    assert unmatched(bds, '{"Messages":null}', []) == "BDS's JSON prints None past the case's last scalar"
    assert unmatched(bds, '{"Messages":null}', [["messages", None]]) is None


def test_a_repeated_scalar_needs_one_appearance_per_entry(bds):
    assert unmatched(bds, '{"A":7}', [["x", 7], ["y", 7]]) == "y is 7 in the case and not in BDS's JSON"


def test_a_map_key_bds_prints_as_a_name_must_be_the_listed_key(bds):
    printed = [["entities.s1", "s1"], ["entities.s1", 10]]
    assert unmatched(bds, '{"Entities":{"s1":10}}', printed) is None
    assert unmatched(bds, '{"Entities":{"s2":10}}', printed) == "entities.s1 is 's1' in the case and 10 in BDS's JSON"


def test_a_bool_does_not_match_a_number(bds):
    assert unmatched(bds, '{"Flag":1}', [["flag", True]]) == "flag is True in the case and 1 in BDS's JSON"


def test_a_whole_number_does_not_match_the_float_bds_shows(bds):
    assert unmatched(bds, '{"Value":2.0}', [["value", 2]]) == "value is 2 in the case and 2.0 in BDS's JSON"


def test_a_float_matches_the_same_float_bds_shows(bds):
    assert unmatched(bds, '{"Value":2.0}', [["value", 2.0]]) is None


def test_a_byte_past_0x7f_matches_the_raw_byte_bds_writes(bds):
    assert unmatched(bds, '{"Chunk Data":"\udc80\\u0001"}', [["data", "\udc80\u0001"]]) is None


def test_a_byte_past_0x7f_does_not_match_its_latin_1_character(bds):
    found = unmatched(bds, '{"Chunk Data":"\u0080"}', [["data", "\udc80"]])
    assert found == "data is '\\udc80' in the case and '\\x80' in BDS's JSON"


COMPOUND = '{"Data":10,"":1,"b":{"data":7},7:"bytes",3:1,254:3,0}'
COMPOUND_PRINTED = [
    ["data", 10],
    ["data", "", True],
    ["data.b", 1, True],
    ["data.b", "b", True],
    ["data.b", 7, True],
    ["data.bytes", 7, True],
    ["data.bytes", "bytes", True],
    ["data.bytes", 3, True],
    ["data.bytes[0]", 1, True],
    ["data.bytes[1]", 254, True],
    ["data.bytes[2]", 3, True],
    ["data", 0, True],
]


def test_a_compound_tag_bds_prints_without_names_agrees_item_by_item(bds):
    assert unmatched(bds, COMPOUND, COMPOUND_PRINTED) is None


def test_a_byte_bds_prints_unsigned_does_not_match_a_signed_byte(bds):
    printed = [["data.bytes[1]", -2, True] if each[0] == "data.bytes[1]" else each for each in COMPOUND_PRINTED]
    assert unmatched(bds, COMPOUND, printed) == "data.bytes[1] is -2 in the case and 254 in BDS's JSON"


def test_a_tag_name_bds_prints_otherwise_is_reported(bds):
    found = unmatched(bds, COMPOUND.replace('"b":', '"c":'), COMPOUND_PRINTED)
    assert found == "data.b is 'b' in the case and 'c' in BDS's JSON"


def test_a_name_after_a_compound_tag_stands_where_the_tags_items_put_it(bds):
    text = '{"Data":10,"":1,"b":{"data":7},0:"Response Type",2}'
    printed = [*(each for each in COMPOUND_PRINTED if not each[0].startswith("data.bytes")), ["response_type", 2]]
    assert unmatched(bds, text, printed) is None
    found = unmatched(bds, text, [each[:2] for each in printed])
    assert found == "response_type is 2 in the case and 'Response Type' in BDS's JSON"


@pytest.fixture(scope="module")
def values():
    pytest.importorskip("bedrock_protocol_compiler")
    spec = importlib.util.spec_from_file_location("goldens_values", SCRIPT.with_name("values.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        ("SemVersion", "version", "1.2.3"),
        ("PackInstanceId", "version", "2.3.4"),
        ("ExperimentToggle", "name", "gametest"),
        ("ExperimentToggle", "enabled", True),
        ("Experiments", "experiments_ever_toggled", True),
        ("Color255RGBA", "a", 128),
        ("SerializableCells", "storage", [1, 2, 3, 4, 5, 6]),
        ("EffectDuration", "value", 600),
        ("NetworkStackLatencyPacket", "create_time", 0),
    ],
    ids=[
        "sem-version",
        "pack-version",
        "experiment-name",
        "experiment-enabled",
        "experiments-ever-toggled",
        "color-alpha",
        "cell-storage",
        "effect-duration",
        "latency-create-time",
    ],
)
def test_a_leaf_bds_normalises_is_generated_as_a_value_bds_keeps(values, schema, name, field, kept):
    chosen = generated(values, schema, name)
    assert [each[field] for each in chosen] == [kept for _ in chosen]


@pytest.mark.parametrize(
    ("name", "field"),
    [
        ("ContentIdentity", "identity"),
        ("PackInstanceId", "pack_id"),
        ("AttributeModifier", "id"),
        ("StartGamePacket", "template_content_identity"),
    ],
    ids=["content-identity", "pack-id", "modifier-id", "template-content-identity"],
)
def test_a_uuid_carried_as_text_is_generated_as_the_text_bds_writes(values, schema, name, field):
    texts = [each[field] for each in generated(values, schema, name)]
    assert texts
    assert texts == [str(uuid.UUID(text)) for text in texts]


def test_level_settings_carry_the_game_rules_bds_writes_in_its_order(values, schema):
    rules = generated(values, schema, "LevelSettings")[0]["game_rules"]["rules"]
    assert (len(rules), rules[0]["name"], rules[-1]["name"]) == (39, "commandBlockOutput", "tntExplosionDropDecay")


@pytest.mark.parametrize(
    ("name", "field", "value", "printed"),
    [
        ("MoveActorAbsoluteData", "rot_x", -43, [["rot_x", 213]]),
        ("ResourcePackDataInfoPacket", "nb_chunks", -593, [["nb_chunks", 4294966703]]),
        ("SetTimePacket", "time", -5, [["time", -5]]),
        ("PlayStatusPacket", "status", "LOGIN_FAILED_CLIENT_OLD", [["status", 1]]),
        ("LevelSettings", "nether_type", "FLAT", [["nether_type", True]]),
        (
            "ServerboundDataDrivenScreenClosedPacket",
            "close_reason",
            "CLIENT_CANCELED",
            [["close_reason", "clientcanceled"]],
        ),
        ("AnimatePacket", "swing_source", "ATTACK", [["swing_source", "attack"]]),
        ("AnimatePacket", "swing_source", None, []),
        ("DisconnectPacket", "messages", None, [["messages", None]]),
        ("ResourcePackClientResponsePacket", "response", {"Cancel": {}}, [["response.Cancel.response_type", "cancel"]]),
        ("CameraAimAssistCategoryPriorities", "entities", {"s1": 10}, [["entities.s1", "s1"], ["entities.s1", 10]]),
        (
            "GraphicsOverrideParameterPacket",
            "keyframes",
            {"0.75": {"x": 1.5, "y": 2.5, "z": 3.5}},
            [["keyframes.0.75", 0.75], ["keyframes.0.75.x", 1.5], ["keyframes.0.75.y", 2.5], ["keyframes.0.75.z", 3.5]],
        ),
        ("SerializableCells", "storage", [1, 2, 128], [["storage", "\x01\x02\udc80"]]),
        ("LevelChunkPacket", "serialized_chunk", "800102", [["serialized_chunk", "\udc80\x01\x02"]]),
        (
            "ServerboundPackSettingChangePacket",
            "pack_id",
            "00000000-0000-0001-0000-000000000002",
            [["pack_id", 1], ["pack_id", 2]],
        ),
        (
            "ContentIdentity",
            "identity",
            "6f0b5e2a-1c3d-4e8f-9a7b-2d4c6e8f0a1b",
            [["identity", "6f0b5e2a-1c3d-4e8f-9a7b-2d4c6e8f0a1b"]],
        ),
        ("ActorDataFlagComponent", "value", 1 | 1 << 13, [["value", 129], ["value", 64, True]]),
        (
            "DataStoreChange",
            "new_data",
            {"k": [1, None]},
            [["new_data.k", "k"], ["new_data.k[0]", 1], ["new_data.k[1]", None]],
        ),
        (
            "BlockActorDataPacket",
            "data",
            {"z": {"ByteTag": 7}, "a": {"ListTag": {"type": 3, "tags": [{"IntTag": 1}]}}},
            [
                ["data", 10],
                ["data", "", True],
                ["data.a", 9, True],
                ["data.a", "a", True],
                ["data.a", 3, True],
                ["data.a", 1, True],
                ["data.a[0]", 1, True],
                ["data.z", 1, True],
                ["data.z", "z", True],
                ["data.z", 7, True],
                ["data", 0, True],
            ],
        ),
        (
            "LevelEventGenericPacket",
            "data",
            {"n": {"CompoundTag": {"s": {"StringTag": "v"}}}},
            [
                ["data.n", 10],
                ["data.n", "n", True],
                ["data.n.s", 8, True],
                ["data.n.s", "s", True],
                ["data.n.s", "v", True],
                ["data.n", 0, True],
                ["data", 0, True],
            ],
        ),
    ],
    ids=[
        "int8-as-uint8",
        "int32-as-uint32",
        "same-signedness",
        "enum-number",
        "bool-enum",
        "name-coded-enum",
        "name-coded-optional",
        "absent-optional",
        "absent-variant",
        "literal-tag",
        "string-key",
        "float-key",
        "byte-vector",
        "blob",
        "uuid",
        "uuid-text",
        "bitset",
        "dynamic-value",
        "compound-tag",
        "compound-tag-data",
    ],
)
def test_a_value_is_listed_as_bds_json_prints_it(values, schema, name, field, value, printed):
    generator = values.Generator(schema, 2168)
    shape = generator.shape(next(each for each in schema.order if each.name == name and (each, 2168) in schema.live))
    assert generator.printed(next(each.type for each in shape.fields if each.name == field), value, field) == printed


@pytest.mark.parametrize(
    ("name", "value", "printed"),
    [
        ("DataItemBytePayload", {"value": 7}, [["type", 0], ["value", 7]]),
        ("InventoryTransaction", {"actions": []}, []),
    ],
    ids=["literal", "true-marker"],
)
def test_a_struct_lists_its_literals_but_not_its_true_markers(values, schema, name, value, printed):
    family = next(each for each in schema.order if each.name == name and (each, 2168) in schema.live)
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
        ("CameraAimAssistPacket", "view_angle", {"x": 45.5, "y": 30.25}),
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
        "aim-view-angle",
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
    ("name", "field", "read"),
    [
        ("CameraSplineDefinition", "name", "test:spline"),
        ("CameraSplineDefinition", "spline_type", "linear"),
    ],
    ids=[
        "spline-name",
        "spline-type",
    ],
)
def test_a_string_bds_reads_only_in_a_form_is_generated_in_it(values, schema, name, field, read):
    assert {each[field] for each in generated(values, schema, name)} - {None} == {read}


@pytest.mark.parametrize(
    ("name", "field"),
    [
        ("AddVolumeEntityPacket", "min_engine_version"),
        ("SerializedSkinRef", "geometry_data_min_engine_version"),
        ("ResourcePackStackPacket", "base_game_version"),
        ("LevelSettings", "base_game_version"),
    ],
    ids=["volume-engine-version", "skin-engine-version", "base-game-version", "level-base-game-version"],
)
def test_a_version_bds_keeps_in_several_forms_takes_each_in_turn(values, schema, name, field):
    generator = values.Generator(schema, 2168)
    shape = generator.shape(next(each for each in schema.order if each.name == name))
    forms = values.KEPT_FORMS[f"{name}.{field}"]
    assert [generator.struct(shape, 0)[field] for _ in range(2 * len(forms))] == [*forms, *forms]


def test_a_handshake_token_is_a_jwt_whose_claims_carry_a_salt(values, schema):
    token = generated(values, schema, "ServerToClientHandshakePacket")[0]["token"]
    segments = [base64.urlsafe_b64decode(each + "=" * (-len(each) % 4)) for each in token.split(".")]
    assert len(segments) == 3
    assert (json.loads(segments[0])["alg"], len(base64.b64decode(json.loads(segments[1])["salt"]))) == ("ES384", 16)


@pytest.mark.parametrize(
    ("name", "field"),
    [
        ("AgentActionEventPacket", "response"),
        ("ModalFormRequestPacket", "form_json"),
        ("ModalFormResponsePacket", "json_response"),
        ("ServerSettingsResponsePacket", "form_json"),
        ("AddBehaviorTreePacket", "json_input"),
        ("NpcDialoguePacket", "action_json"),
        ("SpawnParticleEffectPacket", "molang_variables"),
        ("SerializedSkinRef", "geometry_data"),
        ("FeatureBinaryJsonFormat", "binary_json_output"),
    ],
    ids=[
        "agent-response",
        "form-request",
        "form-response",
        "settings-form",
        "behavior-tree",
        "npc-actions",
        "molang-variables",
        "skin-geometry",
        "feature-json",
    ],
)
def test_a_json_member_is_generated_as_json_that_holds_something(values, schema, name, field):
    texts = [each[field] for each in generated(values, schema, name) if each[field] is not None]
    assert texts
    assert [json.loads(text) in (None, [], {}) for text in texts] == [False for _ in texts]


def test_a_login_carries_the_protocol_number_of_its_version(values, schema):
    login = next(each for each in schema.order if each.name == "LoginPacket")
    versions = [version for version in schema.versions if (login, version) in schema.live]
    numbers = [values.values_of(schema, version, login)[0][0]["client_network_version"] for version in versions]
    assert numbers == versions


@pytest.mark.parametrize(
    ("name", "authentication"), [("LoginPacket", 0), ("SubClientLoginPacket", 1)], ids=["login", "sub-client"]
)
def test_a_connection_request_frames_the_authentication_json_and_a_client_data_token(
    values, schema, name, authentication
):
    request = bytes.fromhex(generated(values, schema, name)[0]["connection_request"])
    size = int.from_bytes(request[:4], "little")
    first, second = request[4 : 4 + size], request[8 + size :]
    assert int.from_bytes(request[4 + size : 8 + size], "little") == len(second)
    assert first.endswith(b"\n")
    assert json.loads(first) == {"AuthenticationType": authentication, "Token": json.loads(first)["Token"]}
    segments = [base64.urlsafe_b64decode(each + "=" * (-len(each) % 4)) for each in second.decode().split(".")]
    assert len(segments) == 3
    assert [type(json.loads(each)) for each in segments[:2]] == [dict, dict]


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


@pytest.mark.parametrize(
    ("name", "field", "accepted"),
    [
        (
            "MessageOnly",
            "type",
            {"RAW", "TIP", "SYSTEM_MESSAGE", "TEXT_OBJECT_WHISPER", "TEXT_OBJECT", "TEXT_OBJECT_ANNOUNCEMENT"},
        ),
        ("AuthorAndMessage", "type", {"CHAT", "WHISPER", "ANNOUNCEMENT"}),
        ("MessageAndParams", "type", {"TRANSLATE", "POPUP", "JUKEBOX_POPUP"}),
        ("RemoveEntry", "action", {"REMOVE"}),
        ("AddEntry", "action", {"ADD"}),
        ("CommandOriginData", "type", {"PLAYER", "DEV_CONSOLE", "TEST", "AUTOMATION_PLAYER"}),
        ("ServerboundLoadingScreenPacket", "serverbound_loading_screen_packet_type", {"START_LOADING_SCREEN"}),
    ],
    ids=[
        "text-message-only",
        "text-author-and-message",
        "text-message-and-params",
        "player-list-remove",
        "player-list-add",
        "command-origin",
        "loading-screen",
    ],
)
def test_an_enum_bds_narrows_to_some_members_is_generated_as_each_of_them(values, schema, name, field, accepted):
    assert {each[field] for each in generated(values, schema, name)} == accepted


def test_an_actor_identifier_list_holds_the_idlist_bds_reads(values, schema):
    chosen = generated(values, schema, "AvailableActorIdentifiersPacket")
    assert [list(each["identifier_list"]) for each in chosen] == [["idlist"] for _ in chosen]


def test_a_craft_result_names_an_item_bds_registers(values, schema):
    chosen = generated(values, schema, "NetworkItemInstanceDescriptorData")
    named = {"ItemNameDescriptorData": {"full_name": "minecraft:stick", "aux_value": 7}}
    assert [each["item_descriptor"] for each in chosen] == [named for _ in chosen]
