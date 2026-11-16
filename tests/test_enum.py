import pytest

import bedrock_protocol
from bedrock_protocol import v729, v748, v827, v1001, v2225


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
        pytest.param(v729.Enchant.Type, v2225.Enchant.Type, id="enchant-type"),
        pytest.param(v729.MapDecoration.Type, v2225.MapDecoration.Type, id="map-decoration-type"),
    ],
)
def test_a_nested_enum_is_one_type_across_its_owners(first, last):
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
        pytest.param("LevelSoundEvent", "MOUNT", 611, id="mount"),
    ],
)
def test_a_member_added_later_exists_at_every_protocol(protocol, enum, member, value):
    assert getattr(protocol, enum)[member].value == value


def test_a_member_removed_later_exists_after_it():
    assert v2225.MinecraftPacketIds.ITEM_COMPONENT_PACKET.value == 162


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
def test_an_enum_is_one_type_at_every_protocol(protocol, name):
    assert getattr(protocol, name) is getattr(v2225, name)


def test_an_enum_belongs_to_the_newest_protocol():
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


def test_a_trailing_count_is_its_library_value_at_every_protocol(protocol):
    assert protocol.MolangVersion.NUM_VALID_VERSIONS.value == 14


def test_a_trailing_sentinel_is_its_library_value_at_every_protocol(protocol):
    assert protocol.LevelSoundEvent.UNDEFINED.value == 615


@pytest.mark.parametrize(
    ("enum", "name"),
    [
        pytest.param("InventoryLayout", "COUNT", id="inventory-layout"),
        pytest.param("MemoryCategory", "MEMORY_CATEGORY_COUNT", id="memory-category"),
        pytest.param("PieceType", "COUNT", id="piece-type"),
    ],
)
def test_a_sentinel_is_no_member(enum, name):
    assert name not in getattr(v2225, enum).__members__


def test_the_number_of_a_sentinel_is_no_member():
    assert 4 not in v2225.InventoryLayout


def test_a_deprecated_member_says_so_in_its_docstring():
    assert v2225.InputMode.MOTION_CONTROLLER_DEPRECATED.__doc__ == "Deprecated."
