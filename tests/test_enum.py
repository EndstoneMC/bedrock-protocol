import pytest

import bedrock_protocol as bp
from bedrock_protocol import v649, v712, v1001


def test_an_enum_member_keeps_its_schema_name():
    assert bp.BossBarColor.REBECCA_PURPLE.name == "REBECCA_PURPLE"


def test_an_enum_member_is_its_integer():
    assert bp.BossBarColor.WHITE.value == 7


def test_a_member_is_found_by_its_schema_name():
    assert bp.BossEventUpdateType["UPDATE_STYLE"] is bp.BossEventUpdateType.UPDATE_STYLE


def test_a_name_no_member_holds_is_not_in_the_enum():
    assert "NOPE" not in bp.BossEventUpdateType.__members__


def test_a_member_is_in_its_enum():
    assert bp.BossBarOverlay.NOTCHED_20 in bp.BossBarOverlay


def test_an_integer_finds_its_member():
    assert bp.BossBarColor(2) is bp.BossBarColor.RED


def test_an_integer_no_member_holds_is_not_in_the_enum():
    assert 8 not in bp.BossBarColor


def test_an_integer_no_member_holds_finds_no_member():
    with pytest.raises(ValueError, match="8 is not a valid BossBarColor"):
        bp.BossBarColor(8)


def test_an_enum_lists_its_members_in_declaration_order():
    overlay = bp.BossBarOverlay
    assert list(overlay) == [
        overlay.PROGRESS,
        overlay.NOTCHED_6,
        overlay.NOTCHED_10,
        overlay.NOTCHED_12,
        overlay.NOTCHED_20,
    ]


def test_a_negative_leading_member_stays_first():
    assert next(iter(bp.MovementEffectType)) is bp.MovementEffectType.INVALID


def test_a_negative_leading_member_keeps_its_value():
    assert bp.MovementEffectType.INVALID.value == -1


@pytest.mark.parametrize("name", ["BossBarOverlay", "MovementEffectType"])
def test_an_enum_is_named_for_its_schema_class(name):
    assert getattr(bp, name).__name__ == name


@pytest.mark.parametrize(
    ("enum", "name"),
    [
        pytest.param(
            bp.ItemUseInventoryTransaction.ActionType, "ItemUseInventoryTransaction.ActionType", id="action-type"
        ),
        pytest.param(
            v712.CerealizedItemUseInventoryTransaction.ActionType,
            "ItemUseInventoryTransaction.ActionType",
            id="cerealized-action-type",
        ),
        pytest.param(
            bp.InventorySource.InventorySourceFlags, "InventorySource.InventorySourceFlags", id="source-flags"
        ),
    ],
)
def test_a_nested_enum_is_qualified_by_its_owner(enum, name):
    assert enum.__qualname__ == name


@pytest.mark.parametrize(
    ("first", "last"),
    [
        pytest.param(
            v712.CerealizedItemUseInventoryTransaction.TriggerType,
            v1001.CerealizedItemUseInventoryTransaction.TriggerType,
            id="trigger-type",
        ),
        pytest.param(
            v712.CerealizedItemUseInventoryTransaction.ActionType,
            bp.ItemUseInventoryTransaction.ActionType,
            id="action-type",
        ),
        pytest.param(v649.AnimatePacket.Action, bp.AnimatePacket.Action, id="animate-action"),
    ],
)
def test_a_nested_enum_is_one_type_across_its_owners(first, last):
    assert first is last


def test_a_nested_enum_holds_its_members():
    assert len(bp.NpcRequestPacket.RequestType) == 7


def test_a_nested_enum_finds_a_member_by_name():
    message = bp.ActorBlockSyncMessage.MessageId
    assert message["CREATE"] is message.CREATE


def test_a_nested_enum_holds_a_member_an_owner_gated():
    assert v712.CerealizedItemUseInventoryTransaction.ActionType.USE_AS_ATTACK.value == 3


def test_a_nested_enum_holds_a_member_the_latest_owner_dropped():
    assert bp.AnimatePacket.Action.ROW_RIGHT.value == 128


@pytest.mark.parametrize(
    ("enum", "member", "value"),
    [
        pytest.param("MovementEffectType", "DOLPHIN_BOOST", 1, id="dolphin-boost"),
        pytest.param("MovementEffectType", "GEYSER_BOOST", 2, id="geyser-boost"),
        pytest.param("DisconnectFailReason", "ASYNC_JOIN_TASK_DENIED", 118, id="async-join-task-denied"),
        pytest.param("LevelSoundEvent", "MOUNT", 611, id="mount"),
    ],
)
def test_an_enum_holds_a_member_added_later(enum, member, value):
    assert getattr(bp, enum)[member].value == value


def test_a_member_removed_later_exists_after_it():
    assert bp.MinecraftPacketIds.ITEM_COMPONENT_PACKET.value == 162


@pytest.mark.parametrize(
    "name",
    [
        "AbilitiesIndex",
        "ActorDamageCause",
        "ActorDataIDs",
        "ActorFlags",
        "ActorType",
        "CurrentCmdVersion",
        "DisconnectFailReason",
        "ItemStackRequestActionType",
        "LevelSoundEvent",
        "MemoryCategory",
        "MinecraftPacketIds",
        "MolangVersion",
        "MovementEffectType",
        "PieceType",
        "PlayerActionType",
    ],
)
def test_no_protocol_holds_an_enum_the_latest_has(protocol, name):
    assert not hasattr(protocol, name)


def test_an_enum_the_latest_protocol_has_belongs_to_the_package():
    assert bp.MovementEffectType.__module__ == "bedrock_protocol"


@pytest.mark.parametrize(
    ("number", "name"),
    [
        pytest.param(162, "ITEM_REGISTRY_PACKET", id="162"),
        pytest.param(328, "PRIMITIVE_SHAPES_PACKET", id="328"),
        pytest.param(330, "CLIENTBOUND_DATA_STORE", id="330"),
        pytest.param(334, "CLIENTBOUND_DATA_DRIVEN_UI_CLOSE_SCREEN", id="334"),
    ],
)
def test_a_value_shared_by_members_never_live_together_finds_the_newest_live_member(number, name):
    assert bp.MinecraftPacketIds(number) is bp.MinecraftPacketIds[name]


def test_a_value_a_pointer_shares_finds_the_pointer():
    assert bp.EditorLevelMigrationVersion(1) is bp.EditorLevelMigrationVersion.CURRENT


def test_a_member_sharing_a_value_with_a_newer_one_equals_it():
    ids = bp.MinecraftPacketIds
    assert ids.ITEM_COMPONENT_PACKET == ids.ITEM_REGISTRY_PACKET


def test_a_member_sharing_a_value_with_a_newer_one_keeps_its_own_name():
    assert bp.MinecraftPacketIds.ITEM_COMPONENT_PACKET.name == "ITEM_COMPONENT_PACKET"


def test_a_trailing_count_is_its_library_value():
    assert bp.MolangVersion.NUM_VALID_VERSIONS.value == 14


def test_a_trailing_sentinel_is_its_library_value():
    assert bp.LevelSoundEvent.UNDEFINED.value == 620


@pytest.mark.parametrize(
    ("enum", "name"),
    [
        pytest.param("InventoryLayout", "COUNT", id="inventory-layout"),
        pytest.param("MemoryCategory", "MEMORY_CATEGORY_COUNT", id="memory-category"),
        pytest.param("PieceType", "COUNT", id="piece-type"),
    ],
)
def test_a_sentinel_is_no_member(enum, name):
    assert name not in getattr(bp, enum).__members__


def test_the_number_of_a_sentinel_is_no_member():
    assert 4 not in bp.InventoryLayout


def test_a_deprecated_member_says_so_in_its_docstring():
    assert bp.InputMode.MOTION_CONTROLLER_DEPRECATED.__doc__ == "Deprecated."
