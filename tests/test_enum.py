import pytest

import bedrock_protocol as bp
from bedrock_protocol import v729, v898, v1001, v2168, v2193, v2225


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
            v729.CerealizedItemUseInventoryTransaction.ActionType,
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
            v729.CerealizedItemUseInventoryTransaction.TriggerType,
            v1001.CerealizedItemUseInventoryTransaction.TriggerType,
            id="trigger-type",
        ),
        pytest.param(
            v729.CerealizedItemUseInventoryTransaction.ActionType,
            bp.ItemUseInventoryTransaction.ActionType,
            id="action-type",
        ),
        pytest.param(v729.AnimatePacket.Action, bp.AnimatePacket.Action, id="animate-action"),
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
    assert v729.CerealizedItemUseInventoryTransaction.ActionType.USE_AS_ATTACK.value == 3


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


def test_a_member_sharing_a_value_with_a_newer_one_equals_it():
    ids = bp.MinecraftPacketIds
    assert ids.ITEM_COMPONENT_PACKET == ids.ITEM_REGISTRY_PACKET


def test_a_member_sharing_a_value_with_a_newer_one_keeps_its_own_name():
    assert bp.MinecraftPacketIds.ITEM_COMPONENT_PACKET.name == "ITEM_COMPONENT_PACKET"


def test_a_trailing_count_is_its_library_value():
    assert bp.MolangVersion.NUM_VALID_VERSIONS.value == 14


def test_a_trailing_sentinel_is_its_library_value():
    assert bp.LevelSoundEvent.UNDEFINED.value == 615


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


@pytest.mark.parametrize(
    ("module", "value", "number"),
    [
        pytest.param(v2225, bp.ContainerType.DISC_PRESS, 38, id="appended-member"),
        pytest.param(v2168, bp.LevelSoundEvent.UNDEFINED, 614, id="member-shifted-later"),
        pytest.param(v2225, bp.LevelSoundEvent.UNDEFINED, 615, id="member-at-its-library-value"),
        pytest.param(v898, bp.ActorDamageCause.DEHYDRATION, 35, id="member-valued-above-its-number"),
        pytest.param(v729, bp.MolangVersion.LATEST, 12, id="derived-member"),
        pytest.param(v2168, bp.PieceType.UNSUPPORTED, 28, id="member-shifted-by-an-insertion"),
        pytest.param(v2193, bp.CurrentCmdVersion.LATEST, 52, id="enum-no-field-numbers"),
    ],
)
def test_a_protocol_numbers_an_enum_value(module, value, number):
    assert module.enum_integer(value) == number


@pytest.mark.parametrize(
    ("module", "value"),
    [
        pytest.param(v2193, bp.ContainerType.DISC_PRESS, id="member-added-later"),
        pytest.param(v2168, bp.LevelSoundEvent.ICE_BALL_BREAK, id="member-inserted-later"),
        pytest.param(v729, bp.ActorDamageCause.DEHYDRATION, id="member-of-a-later-span"),
        pytest.param(v2168, bp.PieceType.CO_CO, id="member-inserted-before-another"),
        pytest.param(v2193, bp.CursorItemDragState.START, id="enum-the-protocol-lacks"),
    ],
)
def test_a_protocol_gives_no_number_to_a_value_it_cannot_encode(module, value):
    assert module.enum_integer(value) is None


def test_a_protocol_cannot_encode_a_value_it_gives_no_number():
    assert not v2193.enum_contains(bp.ContainerType.DISC_PRESS)


def test_a_protocol_can_encode_a_value_it_numbers():
    assert v2225.enum_contains(bp.ContainerType.DISC_PRESS)


def test_a_number_reads_as_the_member_the_protocol_gives_it():
    assert v729.enum_cast(bp.MolangVersion, 12) is bp.MolangVersion.LEAF_SUPPORTING_IN_FIRST_SOLID_BLOCK_BELOW


def test_a_number_no_member_holds_reads_as_an_int():
    assert type(v2225.enum_cast(bp.ContainerType, 100)) is int


def test_a_number_the_protocol_cannot_place_reads_as_none():
    assert v2168.enum_cast(bp.ContainerID, 126) is None


def test_a_protocol_cannot_decode_a_number_it_cannot_place():
    assert not v2168.enum_contains(bp.ContainerID, 126)


def test_a_number_of_an_enum_the_protocol_lacks_reads_as_none():
    assert v2193.enum_cast(bp.CursorItemDragState, 0) is None


def test_a_protocol_lists_the_values_it_can_encode_in_declaration_order():
    assert v2225.enum_values(bp.CursorItemDragState) == (bp.CursorItemDragState.START, bp.CursorItemDragState.STOP)


def test_a_protocol_lists_no_value_of_an_enum_it_lacks():
    assert v2193.enum_values(bp.CursorItemDragState) == ()


def test_a_protocol_leaves_out_a_value_it_cannot_encode():
    assert bp.ContainerType.DISC_PRESS not in v2193.enum_values(bp.ContainerType)


def test_a_value_two_members_share_is_listed_once():
    assert v2225.enum_values(bp.MolangVersion).count(bp.MolangVersion.LATEST) == 1


def test_a_protocol_counts_the_values_it_lists(protocol):
    assert protocol.enum_count(bp.LevelSoundEvent) == len(protocol.enum_values(bp.LevelSoundEvent))


def test_a_protocol_counts_one_value_fewer_where_it_lacks_one():
    assert v2193.enum_count(bp.ContainerType) == v2225.enum_count(bp.ContainerType) - 1


def test_enum_integer_rejects_a_value_that_is_no_enum():
    with pytest.raises(TypeError, match=r"^value: <class 'int'> is not an enum$"):
        v2225.enum_integer(5)


def test_enum_cast_rejects_a_class_that_is_no_enum():
    with pytest.raises(TypeError, match=r"^cls: <class 'bedrock_protocol.TextPacket'> is not an enum$"):
        v2225.enum_cast(bp.TextPacket, 0)


def test_enum_cast_rejects_a_number_its_enum_cannot_hold():
    with pytest.raises(TypeError, match=r"^number: cannot hold 300$"):
        v2225.enum_cast(bp.ContainerType, 300)
