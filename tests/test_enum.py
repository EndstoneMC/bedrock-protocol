import pytest

import bedrock_protocol
from bedrock_protocol import v729, v748, v786, v827, v975, v1001, v2168, v2225


def test_an_enum_member_keeps_its_schema_name(protocol):
    assert protocol.BossBarColor.REBECCA_PURPLE.name == "REBECCA_PURPLE"


def test_an_enum_member_is_its_integer(protocol):
    assert protocol.BossBarColor.WHITE.value == 7


def test_a_member_is_found_by_its_schema_name(protocol):
    assert protocol.BossEventUpdateType["UPDATE_STYLE"] is protocol.BossEventUpdateType.UPDATE_STYLE


def test_a_name_no_member_holds_is_not_in_the_enum(protocol):
    assert "NOPE" not in protocol.BossEventUpdateType.__members__


def test_a_member_is_in_its_enum(protocol):
    assert protocol.BossBarOverlay.NOTCHED_20 in protocol.BossBarOverlay


def test_an_integer_finds_its_member(protocol):
    assert protocol.BossBarColor(2) is protocol.BossBarColor.RED


def test_an_integer_no_member_holds_is_not_in_the_enum(protocol):
    assert 8 not in protocol.BossBarColor


def test_an_integer_no_member_holds_finds_no_member(protocol):
    with pytest.raises(ValueError, match="8 is not a valid BossBarColor"):
        protocol.BossBarColor(8)


def test_an_enum_lists_its_members_in_declaration_order(protocol):
    overlay = protocol.BossBarOverlay
    assert list(overlay) == [
        overlay.PROGRESS,
        overlay.NOTCHED_6,
        overlay.NOTCHED_10,
        overlay.NOTCHED_12,
        overlay.NOTCHED_20,
    ]


def test_a_negative_leading_member_stays_first(protocol):
    assert next(iter(protocol.MovementEffectType)) is protocol.MovementEffectType.INVALID


def test_a_negative_leading_member_keeps_its_value(protocol):
    assert protocol.MovementEffectType.INVALID.value == -1


@pytest.mark.parametrize("name", ["BossBarOverlay", "MovementEffectType"])
def test_an_enum_is_named_for_its_schema_class(protocol, name):
    assert getattr(protocol, name).__name__ == name


@pytest.mark.parametrize(
    ("enum", "name"),
    [
        pytest.param(
            v2225.ItemUseInventoryTransaction.ActionType, "ItemUseInventoryTransaction.ActionType", id="action-type"
        ),
        pytest.param(
            v827.CerealizedItemUseInventoryTransaction.ActionType,
            "ItemUseInventoryTransaction.ActionType",
            id="cerealized-action-type",
        ),
        pytest.param(
            v2225.InventorySource.InventorySourceFlags, "InventorySource.InventorySourceFlags", id="source-flags"
        ),
    ],
)
def test_a_nested_enum_is_qualified_by_its_owner(enum, name):
    assert enum.__qualname__ == name


@pytest.mark.parametrize(
    ("first", "last"),
    [
        pytest.param(
            v827.CerealizedItemUseInventoryTransaction.TriggerType,
            v1001.CerealizedItemUseInventoryTransaction.TriggerType,
            id="trigger-type",
        ),
        pytest.param(
            v827.CerealizedItemUseInventoryTransaction.ActionType,
            v2225.ItemUseInventoryTransaction.ActionType,
            id="action-type",
        ),
        pytest.param(v729.AnimatePacket.Action, v2225.AnimatePacket.Action, id="animate-action"),
    ],
)
def test_a_nested_enum_whose_numbers_never_move_is_one_type_across_its_owners(first, last):
    assert first is last


def test_a_nested_enum_holds_its_members(protocol):
    assert len(protocol.NpcRequestPacket.RequestType) == 7


def test_a_nested_enum_finds_a_member_by_name(protocol):
    message = protocol.ActorBlockSyncMessage.MessageId
    assert message["CREATE"] is message.CREATE


def test_a_nested_enum_holds_a_member_an_owner_gated():
    assert v827.CerealizedItemUseInventoryTransaction.ActionType.USE_AS_ATTACK.value == 3


def test_a_nested_enum_holds_a_member_the_latest_owner_dropped():
    assert v2225.AnimatePacket.Action.ROW_RIGHT.value == 128


@pytest.mark.parametrize(
    ("enum", "member", "value"),
    [
        pytest.param("MovementEffectType", "DOLPHIN_BOOST", 1, id="dolphin-boost"),
        pytest.param("MovementEffectType", "GEYSER_BOOST", 2, id="geyser-boost"),
        pytest.param("DisconnectFailReason", "ASYNC_JOIN_TASK_DENIED", 118, id="async-join-task-denied"),
    ],
)
def test_a_member_added_later_exists_at_every_protocol(protocol, enum, member, value):
    assert getattr(protocol, enum)[member].value == value


def test_a_member_removed_later_exists_after_it():
    assert v2225.MinecraftPacketIds.ITEM_COMPONENT_PACKET.value == 162


@pytest.mark.parametrize("name", ["DisconnectFailReason", "MinecraftPacketIds", "MovementEffectType"])
def test_an_enum_whose_numbers_never_move_is_one_type_at_every_protocol(protocol, name):
    assert getattr(protocol, name) is getattr(v2225, name)


def test_an_enum_whose_numbers_never_move_belongs_to_the_newest_protocol():
    assert v748.MovementEffectType.__module__ == f"bedrock_protocol.v{bedrock_protocol.versions[-1]}"


@pytest.mark.parametrize(
    ("number", "name"),
    [
        pytest.param(162, "ITEM_REGISTRY_PACKET", id="162"),
        pytest.param(328, "PRIMITIVE_SHAPES_PACKET", id="328"),
        pytest.param(330, "CLIENTBOUND_DATA_STORE", id="330"),
        pytest.param(334, "CLIENTBOUND_DATA_DRIVEN_UI_CLOSE_SCREEN", id="334"),
    ],
)
def test_a_value_shared_by_members_never_live_together_finds_the_newest_live_member(protocol, number, name):
    assert protocol.MinecraftPacketIds(number) is protocol.MinecraftPacketIds[name]


def test_a_member_sharing_a_value_with_a_newer_one_equals_it():
    ids = v2225.MinecraftPacketIds
    assert ids.ITEM_COMPONENT_PACKET == ids.ITEM_REGISTRY_PACKET


def test_a_member_sharing_a_value_with_a_newer_one_keeps_its_own_name():
    assert v2225.MinecraftPacketIds.ITEM_COMPONENT_PACKET.name == "ITEM_COMPONENT_PACKET"


@pytest.mark.parametrize(
    ("member", "value"),
    [
        pytest.param(v786.MolangVersion.NUM_VALID_VERSIONS, 13, id="v786"),
        pytest.param(v827.MolangVersion.NUM_VALID_VERSIONS, 14, id="v827"),
    ],
)
def test_a_trailing_count_follows_the_members_of_its_snapshot(member, value):
    assert member == value


@pytest.mark.parametrize(
    ("first", "last"),
    [
        pytest.param(v786.MolangVersion, v827.MolangVersion, id="molang-version"),
        pytest.param(v1001.LevelSoundEvent, v2168.LevelSoundEvent, id="level-sound-event"),
    ],
)
def test_a_renumbered_enum_is_one_type_per_set_of_members(first, last):
    assert first is not last


@pytest.mark.parametrize(
    ("enum", "name"),
    [
        pytest.param(v975.LevelSoundEvent, "MOUNT", id="v975-mount"),
        pytest.param(v1001.LevelSoundEvent, "MOUNT", id="v1001-mount"),
        pytest.param(v1001.LevelSoundEvent, "DISMOUNT", id="v1001-dismount"),
        pytest.param(v1001.LevelSoundEvent, "STRAW_BED_BREAK_LEAVE", id="v1001-straw-bed-break-leave"),
    ],
)
def test_the_level_sound_events_added_at_2168_are_absent_before_it(enum, name):
    assert name not in enum.__members__


@pytest.mark.parametrize(
    ("member", "value"),
    [
        pytest.param(v2168.LevelSoundEvent.MOUNT, 611, id="mount"),
        pytest.param(v2168.LevelSoundEvent.DISMOUNT, 612, id="dismount"),
        pytest.param(v2168.LevelSoundEvent.STRAW_BED_BREAK_LEAVE, 613, id="straw-bed-break-leave"),
    ],
)
def test_the_level_sound_events_added_at_2168_take_the_sentinel_slots(member, value):
    assert member == value


@pytest.mark.parametrize(
    ("member", "value"),
    [
        pytest.param(v975.LevelSoundEvent.UNDEFINED, 601, id="v975"),
        pytest.param(v1001.LevelSoundEvent.UNDEFINED, 611, id="v1001"),
        pytest.param(v2168.LevelSoundEvent.UNDEFINED, 614, id="v2168"),
    ],
)
def test_the_trailing_undefined_sentinel_follows_the_members_of_its_snapshot(member, value):
    assert member == value


def test_2168_adds_three_level_sound_events():
    assert len(v2168.LevelSoundEvent) == len(v1001.LevelSoundEvent) + 3


def test_a_sentinel_is_no_member():
    assert "COUNT" not in v2225.InventoryLayout.__members__


def test_the_number_of_a_sentinel_is_no_member():
    assert 4 not in v2225.InventoryLayout


def test_a_deprecated_member_says_so_in_its_docstring():
    assert v2225.InputMode.MOTION_CONTROLLER_DEPRECATED.__doc__ == "Deprecated."
