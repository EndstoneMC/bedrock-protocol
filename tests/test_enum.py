import pytest

from bedrock_protocol import v748, v786, v827, v844, v975, v1001, v2168, v2225


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
            v2225.InventorySource.InventorySourceFlags, "InventorySource.InventorySourceFlags", id="source-flags"
        ),
    ],
)
def test_a_nested_enum_is_qualified_by_its_owner(enum, name):
    assert enum.__qualname__ == name


def test_an_ungated_nested_enum_is_one_type_across_snapshots():
    assert v827.ItemUseInventoryTransaction.TriggerType is v1001.ItemUseInventoryTransaction.TriggerType


def test_a_nested_enum_holds_its_members(protocol):
    assert len(protocol.ItemUseInventoryTransaction.TriggerType) == 3


def test_a_nested_enum_finds_a_member_by_name(protocol):
    result = protocol.ItemUseInventoryTransaction.PredictedResult
    assert result["SUCCESS"] is result.SUCCESS


def test_a_nested_enum_that_gates_a_member_is_a_type_per_snapshot():
    assert v827.ItemUseInventoryTransaction.ActionType is not v1001.ItemUseInventoryTransaction.ActionType


@pytest.mark.parametrize(
    ("enum", "count"),
    [
        pytest.param(v827.ItemUseInventoryTransaction.ActionType, 3, id="v827-action-type"),
        pytest.param(v844.ItemUseInventoryTransaction.ActionType, 4, id="v844-action-type"),
        pytest.param(v748.MovementEffectType, 3, id="v748-movement-effect"),
        pytest.param(v786.MovementEffectType, 4, id="v786-movement-effect"),
        pytest.param(v1001.MovementEffectType, 5, id="v1001-movement-effect"),
    ],
)
def test_a_versioned_enum_holds_the_members_of_its_snapshot(enum, count):
    assert len(enum) == count


def test_a_member_added_later_is_absent_before_it():
    assert "GEYSER_BOOST" not in v748.MovementEffectType.__members__


@pytest.mark.parametrize(
    ("member", "value"),
    [
        pytest.param(v975.MovementEffectType.COUNT, 2, id="v975"),
        pytest.param(v1001.MovementEffectType.COUNT, 3, id="v1001"),
    ],
)
def test_a_trailing_count_follows_the_members_of_its_snapshot(member, value):
    assert member == value


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
