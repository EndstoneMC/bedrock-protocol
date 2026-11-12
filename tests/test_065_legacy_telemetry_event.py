import pytest

from bedrock_protocol import v859, v2168

MOB_KILLED = bytes.fromhex("090801040204fe04040106747261646572")

ITEM_USED = bytes.fromhex("0e3e00142c01050000000100000002000000")

POI_CAULDRON_USED = bytes.fromhex("0e1e000a092c01")

CAULDRON_USED = bytes.fromhex("0e0a000505feff2c01")

ACHIEVEMENT = bytes.fromhex("0e00000014")

HONEY_HARVESTED = bytes.fromhex("0e2c0015")

# BDS 1.21.124.2 (protocol 860) LegacyTelemetryEventPacket::write: no variant index, the event type picks the body,
# and the enums and int16 members go through BinaryStream's zigzag varint32
BEFORE_ACHIEVEMENT = bytes.fromhex("0e000028")
BEFORE_INTERACTION = bytes.fromhex("0e02000208fe040003")
BEFORE_CAULDRON_USED = bytes.fromhex("0e0a000503d804")
BEFORE_POI_CAULDRON_USED = bytes.fromhex("0e1e0012d804")
BEFORE_COMPOSTER_USED = bytes.fromhex("0e200026d804")
BEFORE_BELL_USED = bytes.fromhex("0e2200d804")
BEFORE_AGENT_COMMAND = bytes.fromhex("0e10000201016101620163")
BEFORE_HONEY_HARVESTED = bytes.fromhex("0e2c00")
BEFORE_ITEM_USED = bytes.fromhex("0e3e002c01050000000100000002000000")

GOLDENS = [
    pytest.param(
        v2168.LegacyTelemetryEventPacket(
            player_unique_id=-5,
            type=v2168.LegacyTelemetryEventPacket.Type.MOB_KILLED,
            use_player_id=True,
            event_data=v2168.LegacyTelemetryEventPacket.MobKilled(
                killer_entity_id=1,
                killed_mob_id=2,
                damage_child_type=v2168.ActorType.PLAYER,
                damage_source=2,
                trader_tier=-1,
                trader_name="trader",
            ),
        ),
        MOB_KILLED,
        id="mob-killed",
    ),
    pytest.param(
        v2168.LegacyTelemetryEventPacket(
            player_unique_id=7,
            type=v2168.LegacyTelemetryEventPacket.Type.ITEM_USED,
            use_player_id=False,
            event_data=v2168.LegacyTelemetryEventPacket.ItemUsed(item_id=300, item_aux=5, use_method=1, count=2),
        ),
        ITEM_USED,
        id="item-used",
    ),
    pytest.param(
        v2168.LegacyTelemetryEventPacket(
            player_unique_id=7,
            type=v2168.LegacyTelemetryEventPacket.Type.POI_CAULDRON_USED,
            use_player_id=False,
            event_data=v2168.LegacyTelemetryEventPacket.POICauldronUsed(
                interaction_type=v2168.MinecraftEventing.POIBlockInteractionType.COOKING, item_id=300
            ),
        ),
        POI_CAULDRON_USED,
        id="poi-cauldron-used",
    ),
    pytest.param(
        v2168.LegacyTelemetryEventPacket(
            player_unique_id=7,
            type=v2168.LegacyTelemetryEventPacket.Type.CAULDRON_USED,
            use_player_id=False,
            event_data=v2168.LegacyTelemetryEventPacket.CauldronUsed(
                contents_color=5, contents_type=-2, fill_level=300
            ),
        ),
        CAULDRON_USED,
        id="cauldron-used",
    ),
    pytest.param(
        v2168.LegacyTelemetryEventPacket(
            player_unique_id=7,
            type=v2168.LegacyTelemetryEventPacket.Type.ACHIEVEMENT,
            use_player_id=False,
            event_data=v2168.LegacyTelemetryEventPacket.Achievement(
                achievement_id=v2168.MinecraftEventing.AchievementIds.IRON_BELLY
            ),
        ),
        ACHIEVEMENT,
        id="achievement",
    ),
    pytest.param(
        v2168.LegacyTelemetryEventPacket(
            player_unique_id=7,
            type=v2168.LegacyTelemetryEventPacket.Type.HONEY_HARVESTED,
            use_player_id=False,
            event_data=v2168.LegacyTelemetryEventPacket.Empty(),
        ),
        HONEY_HARVESTED,
        id="honey-harvested",
    ),
]

BEFORE_GOLDENS = [
    pytest.param(
        v859.LegacyTelemetryEventPacket(
            player_unique_id=7,
            type=v859.LegacyTelemetryEventPacket.Type.ACHIEVEMENT,
            use_player_id=False,
            achievement=v859.LegacyTelemetryEventPacket.Achievement(
                achievement_id=v859.MinecraftEventing.AchievementIds.IRON_BELLY
            ),
        ),
        BEFORE_ACHIEVEMENT,
        id="achievement",
    ),
    pytest.param(
        v859.LegacyTelemetryEventPacket(
            player_unique_id=7,
            type=v859.LegacyTelemetryEventPacket.Type.INTERACTION,
            use_player_id=False,
            interaction=v859.LegacyTelemetryEventPacket.Interaction(
                interacted_entity_id=1,
                interaction_type=v859.MinecraftEventing.InteractionType.CRAFTED,
                interacted_entity_type=319,
                interacted_entity_variant=0,
                interacted_entity_color=3,
            ),
        ),
        BEFORE_INTERACTION,
        id="interaction",
    ),
    pytest.param(
        v859.LegacyTelemetryEventPacket(
            player_unique_id=7,
            type=v859.LegacyTelemetryEventPacket.Type.CAULDRON_USED,
            use_player_id=False,
            cauldron_used=v859.LegacyTelemetryEventPacket.CauldronUsed(
                contents_color=5, contents_type=-2, fill_level=300
            ),
        ),
        BEFORE_CAULDRON_USED,
        id="cauldron-used",
    ),
    pytest.param(
        v859.LegacyTelemetryEventPacket(
            player_unique_id=7,
            type=v859.LegacyTelemetryEventPacket.Type.POI_CAULDRON_USED,
            use_player_id=False,
            poi_cauldron_used=v859.LegacyTelemetryEventPacket.POICauldronUsed(
                interaction_type=v859.MinecraftEventing.POIBlockInteractionType.COOKING, item_id=300
            ),
        ),
        BEFORE_POI_CAULDRON_USED,
        id="poi-cauldron-used",
    ),
    pytest.param(
        v859.LegacyTelemetryEventPacket(
            player_unique_id=7,
            type=v859.LegacyTelemetryEventPacket.Type.COMPOSTER_USED,
            use_player_id=False,
            composter_used=v859.LegacyTelemetryEventPacket.ComposterUsed(
                interaction_type=v859.MinecraftEventing.POIBlockInteractionType.COMPOST_ITEM_PLACED, item_id=300
            ),
        ),
        BEFORE_COMPOSTER_USED,
        id="composter-used",
    ),
    pytest.param(
        v859.LegacyTelemetryEventPacket(
            player_unique_id=7,
            type=v859.LegacyTelemetryEventPacket.Type.BELL_USED,
            use_player_id=False,
            bell_used=v859.LegacyTelemetryEventPacket.BellUsed(item_id=300),
        ),
        BEFORE_BELL_USED,
        id="bell-used",
    ),
    pytest.param(
        v859.LegacyTelemetryEventPacket(
            player_unique_id=7,
            type=v859.LegacyTelemetryEventPacket.Type.AGENT_COMMAND_OBSOLETE,
            use_player_id=False,
            agent_command_obsolete=v859.LegacyTelemetryEventPacket.AgentCommandObsolete(
                int_1=1, int_2=-1, text_1="a", text_2="b", text_3="c"
            ),
        ),
        BEFORE_AGENT_COMMAND,
        id="agent-command",
    ),
    pytest.param(
        v859.LegacyTelemetryEventPacket(
            player_unique_id=7,
            type=v859.LegacyTelemetryEventPacket.Type.HONEY_HARVESTED,
            use_player_id=False,
        ),
        BEFORE_HONEY_HARVESTED,
        id="honey-harvested",
    ),
    pytest.param(
        v859.LegacyTelemetryEventPacket(
            player_unique_id=7,
            type=v859.LegacyTelemetryEventPacket.Type.ITEM_USED,
            use_player_id=False,
            item_used=v859.LegacyTelemetryEventPacket.ItemUsed(item_id=300, item_aux=5, use_method=1, count=2),
        ),
        BEFORE_ITEM_USED,
        id="item-used",
    ),
]


@pytest.mark.parametrize(("packet", "golden"), GOLDENS)
def test_legacy_telemetry_event_encodes_to_its_golden(packet, golden):
    assert bytes(packet) == golden


@pytest.mark.parametrize(("packet", "golden"), GOLDENS)
def test_legacy_telemetry_event_decodes_from_its_golden(packet, golden):
    assert type(packet).from_bytes(golden) == packet


@pytest.mark.parametrize(("packet", "golden"), BEFORE_GOLDENS)
def test_legacy_telemetry_event_encodes_to_its_golden_before_the_cerealisation(packet, golden):
    assert bytes(packet) == golden


@pytest.mark.parametrize(("packet", "golden"), BEFORE_GOLDENS)
def test_legacy_telemetry_event_decodes_from_its_golden_before_the_cerealisation(packet, golden):
    assert type(packet).from_bytes(golden) == packet
