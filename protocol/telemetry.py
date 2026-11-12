"""Legacy telemetry events and the MinecraftEventing enum namespace: Events/."""

from enum import IntEnum

from protocol import field, int16, int32, packet, sentinel, type, uint8, uvarint32, value, varint32
from protocol.actor import ActorType, ActorUniqueID

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"


class MinecraftEventing:
    class InteractionType(IntEnum, uint8):
        BREEDING = 1
        TAMING = 2
        CURING = 3
        CRAFTED = 4
        SHEARING = 5
        MILKING = 6
        TRADING = 7
        FEEDING = 8
        IGNITING = 9
        COLORING = 10
        NAMING = 11
        LEASHING = 12
        UNLEASHING = 13
        PET_SLEEP = 14
        TRUSTING = 15
        COMMANDING = 16
        EQUIPPING = value(17, since=1001)

    class AchievementIds(IntEnum, uint8):
        CHEST_FULL_OF_COBBLESTONE = 7
        DIAMOND_FOR_YOU = 10
        IRON_BELLY = 20
        IRON_MAN = 21
        ON_A_RAIL = 29
        OVERKILL = 30
        RETURN_TO_SENDER = 37
        SNIPER_DUEL = 38
        STAYIN_FROSTY = 39
        TAKE_INVENTORY = 40
        MAP_ROOM = 50
        FREIGHT_STATION = 52
        SMELT_EVERYTHING = 53
        TASTE_OF_YOUR_OWN_MEDICINE = 54
        WHEN_PIGS_FLY = 56
        INCEPTION = 58
        ARTIFICIAL_SELECTION = 60
        FREE_DIVER = 61
        SPAWN_THE_WITHER = 62
        BEACONATOR = 63
        GREAT_VIEW = 64
        SUPER_SONIC = 65
        THE_END_AGAIN = 66
        TREASURE_HUNTER = 67
        SHOOTING_STAR = 68
        FASHION_SHOW = 69
        BRILLIANCE = value(70, until=776)
        SELF_PUBLISHED_AUTHOR = 71
        ALTERNATIVE_FUEL = 72
        SLEEP_WITH_THE_FISHES = 73
        CASTAWAY = 74
        IM_A_MARINE_BIOLOGIST = 75
        SAIL_THE_7_SEAS = 76
        ME_GOLD = 77
        AHOY = 78
        ATLANTIS = 79
        ONE_PICKLE_TWO_PICKLE_SEA_PICKLE_FOUR = 80
        DOA_BARREL_ROLL = 81
        MOSKSTRAUMEN = 82
        ECHOLOCATION = 83
        WHERE_HAVE_YOU_BEEN = 84
        TOP_OF_THE_WORLD = 85
        FRUIT_ON_THE_LOOM = 86
        SOUND_THE_ALARM = 87
        BUY_LOW_SELL_HIGH = 88
        DISENCHANTED = 89
        TIME_FOR_STEW = 90
        BEE_OUR_GUEST = 91
        TOTAL_BEE_LOCATION = 92
        STICKY_SITUATION = 93
        COVER_ME_IN_DEBRIS = 94
        FLOAT_YOUR_GOAT = 95
        FRIEND = 96
        WAX_ON_WAX_OFF = 97
        STRIDER_RIDDEN_IN_LAVA_IN_OVERWORLD = 98
        GOAT_HORN_ACQUIRED = 99
        JUKEBOX_USED_IN_MEADOWS = 100
        TRADED_AT_WORLD_HEIGHT = 101
        SURVIVED_FALL_FROM_WORLD_HEIGHT = 102
        SNEAK_CLOSE_TO_SCULK_SENSOR = 103
        IT_SPREADS = 104
        BIRTHDAY_SONG = 105
        WITH_OUR_POWERS_COMBINED = 106
        PLANTING_THE_PAST = 107
        CAREFUL_RESTORATION = 108
        REVAULTING = 109
        CRAFTERS_CRAFTING_CRAFTERS = 110
        WHO_NEEDS_ROCKETS = 111
        OVER_OVERKILL = 112
        HEART_TRANSPLANTER = value(113, since=766)
        STAY_HYDRATED = value(114, since=818)
        MOB_KABOB = value(115, since=898)
        ADVENTURING_TIME = value(116, since=924)
        UH_OH = value(117, since=1001)
        with value(since=2168):
            GETTING_WOOD = 118
            BENCH_MAKING = 119
            TIME_TO_MINE = 120
            HOT_TOPIC = 121
            ACQUIRE_HARDWARE = 122
            GETTING_AN_UPGRADE = 123
            MONSTER_HUNTER = 124
            DIAMONDS = 125
            PLETHORA_OF_CATS = 126
        WHAT_GOES_AROUND_COMES_AROUND = value(127, since=2225)
        COUNT = sentinel()

    class POIBlockInteractionType(IntEnum, uint8):
        NONE = 0
        EXTEND = 1
        CLONE = 2
        LOCK = 3
        CREATE = 4
        CREATE_LOCATOR = 5
        RENAME = 6
        ITEM_PLACED = 7
        ITEM_REMOVED = 8
        COOKING = 9
        DOUSING = 10
        LIGHTING = 11
        HAYSTACK = 12
        FILLED = 13
        EMPTIED = 14
        ADD_DYE = 15
        DYE_ITEM = 16
        CLEAR_ITEM = 17
        ENCHANT_ARROW = 18
        COMPOST_ITEM_PLACED = 19
        RECOVERED_BONEMEAL = 20
        BOOK_PLACED = 21
        BOOK_OPENED = 22
        DISENCHANT = 23
        REPAIR = 24
        DISENCHANT_AND_REPAIR = 25


@packet(id=65)
class LegacyTelemetryEventPacket:
    class Type(IntEnum, int32):
        ACHIEVEMENT = 0
        INTERACTION = 1
        PORTAL_CREATED = 2
        PORTAL_USED = 3
        MOB_KILLED = 4
        CAULDRON_USED = 5
        PLAYER_DIED = 6
        BOSS_KILLED = 7
        AGENT_COMMAND_OBSOLETE = 8
        AGENT_CREATED = 9
        PATTERN_REMOVED_OBSOLETE = 10
        SLASH_COMMAND = 11
        FISH_BUCKETED_OBSOLETE = 12
        MOB_BORN = 13
        PET_DIED_OBSOLETE = 14
        POI_CAULDRON_USED = value(15, cpp_name="POICauldronUsed")
        COMPOSTER_USED = 16
        BELL_USED = 17
        ACTOR_DEFINITION = 18
        RAID_UPDATE = 19
        PLAYER_MOVEMENT_ANOMALY_OBSOLETE = 20
        PLAYER_MOVEMENT_CORRECTED_OBSOLETE = 21
        HONEY_HARVESTED = 22
        TARGET_BLOCK_HIT = 23
        PIGLIN_BARTER = 24
        PLAYER_WAXED_OR_UNWAXED_COPPER = 25
        CODE_BUILDER_RUNTIME_ACTION = 26
        CODE_BUILDER_SCOREBOARD = 27
        STRIDER_RIDDEN_IN_LAVA_IN_OVERWORLD = 28
        SNEAK_CLOSE_TO_SCULK_SENSOR = 29
        CAREFUL_RESTORATION = 30
        ITEM_USED = 31

    class Achievement:
        achievement_id: MinecraftEventing.AchievementIds = field(type=varint32, until=898)
        achievement_id: MinecraftEventing.AchievementIds = field(since=898)

    class Interaction:
        interacted_entity_id: ActorUniqueID
        interaction_type: MinecraftEventing.InteractionType = field(type=varint32, until=898)
        interaction_type: MinecraftEventing.InteractionType = field(since=898)
        interacted_entity_type: varint32
        interacted_entity_variant: varint32
        interacted_entity_color: uint8

    @type(until=898)
    class AgentCommandObsolete:
        int_1: varint32
        int_2: varint32
        text_1: str
        text_2: str
        text_3: str

    class PortalCreated:
        built_in_dimension: varint32

    class PortalUsed:
        from_dimension: varint32
        to_dimension: varint32

    class MobKilled:
        killer_entity_id: ActorUniqueID
        killed_mob_id: ActorUniqueID
        damage_child_type: ActorType
        damage_source: varint32
        trader_tier: varint32
        trader_name: str

    class CauldronUsed:
        contents_color: uvarint32
        contents_type: int16 = field(type=varint32, until=898)
        contents_type: int16 = field(since=898)
        fill_level: int16 = field(type=varint32, until=898)
        fill_level: int16 = field(since=898)

    class PlayerDied:
        killer_id: varint32
        killer_variant: varint32
        damage_source: varint32
        in_raid: bool

    class BossKilled:
        boss_unique_id: ActorUniqueID
        party_size: varint32
        boss_type: varint32

    class SlashCommand:
        success_count: varint32
        error_count: varint32
        command_name: str
        error_list: str

    class MobBorn:
        baby_type: varint32
        baby_variant: varint32
        baby_color: uint8

    class POICauldronUsed:
        interaction_type: MinecraftEventing.POIBlockInteractionType = field(type=varint32, until=898)
        interaction_type: MinecraftEventing.POIBlockInteractionType = field(since=898)
        item_id: int16 = field(type=varint32, until=898)
        item_id: int16 = field(since=898)

    class ComposterUsed:
        interaction_type: MinecraftEventing.POIBlockInteractionType = field(type=varint32, until=898)
        interaction_type: MinecraftEventing.POIBlockInteractionType = field(since=898)
        item_id: int16 = field(type=varint32, until=898)
        item_id: int16 = field(since=898)

    class BellUsed:
        item_id: int16 = field(type=varint32, until=898)
        item_id: int16 = field(since=898)

    class ActorDefinition:
        event_name: str

    class RaidUpdate:
        current_wave: varint32
        total_waves: varint32
        success: bool

    class TargetBlockHit:
        redstone_level: varint32

    class PiglinBarter:
        item_id: varint32
        was_targeting_bartering_player: bool

    class PlayerWaxedOrUnwaxedCopper:
        block_id: varint32

    class CodeBuilderRuntimeAction:
        runtime_action: str

    class CodeBuilderScoreboard:
        objective_name: str
        score: varint32

    class ItemUsed:
        item_id: int16
        item_aux: int32
        use_method: int32
        count: int32

    @type(since=898)
    class Empty:
        pass

    player_unique_id: ActorUniqueID
    type: Type
    use_player_id: bool
    achievement: Achievement = field(until=898, when=lambda p: p.type == Type.ACHIEVEMENT)
    interaction: Interaction = field(until=898, when=lambda p: p.type == Type.INTERACTION)
    portal_created: PortalCreated = field(until=898, when=lambda p: p.type == Type.PORTAL_CREATED)
    portal_used: PortalUsed = field(until=898, when=lambda p: p.type == Type.PORTAL_USED)
    mob_killed: MobKilled = field(until=898, when=lambda p: p.type == Type.MOB_KILLED)
    cauldron_used: CauldronUsed = field(until=898, when=lambda p: p.type == Type.CAULDRON_USED)
    player_died: PlayerDied = field(until=898, when=lambda p: p.type == Type.PLAYER_DIED)
    boss_killed: BossKilled = field(until=898, when=lambda p: p.type == Type.BOSS_KILLED)
    agent_command_obsolete: AgentCommandObsolete = field(
        until=898, when=lambda p: p.type == Type.AGENT_COMMAND_OBSOLETE
    )
    slash_command: SlashCommand = field(until=898, when=lambda p: p.type == Type.SLASH_COMMAND)
    mob_born: MobBorn = field(until=898, when=lambda p: p.type == Type.MOB_BORN)
    poi_cauldron_used: POICauldronUsed = field(until=898, when=lambda p: p.type == Type.POI_CAULDRON_USED)
    composter_used: ComposterUsed = field(until=898, when=lambda p: p.type == Type.COMPOSTER_USED)
    bell_used: BellUsed = field(until=898, when=lambda p: p.type == Type.BELL_USED)
    actor_definition: ActorDefinition = field(until=898, when=lambda p: p.type == Type.ACTOR_DEFINITION)
    raid_update: RaidUpdate = field(until=898, when=lambda p: p.type == Type.RAID_UPDATE)
    target_block_hit: TargetBlockHit = field(until=898, when=lambda p: p.type == Type.TARGET_BLOCK_HIT)
    piglin_barter: PiglinBarter = field(until=898, when=lambda p: p.type == Type.PIGLIN_BARTER)
    player_waxed_or_unwaxed_copper: PlayerWaxedOrUnwaxedCopper = field(
        until=898, when=lambda p: p.type == Type.PLAYER_WAXED_OR_UNWAXED_COPPER
    )
    code_builder_runtime_action: CodeBuilderRuntimeAction = field(
        until=898, when=lambda p: p.type == Type.CODE_BUILDER_RUNTIME_ACTION
    )
    code_builder_scoreboard: CodeBuilderScoreboard = field(
        until=898, when=lambda p: p.type == Type.CODE_BUILDER_SCOREBOARD
    )
    item_used: ItemUsed = field(until=898, when=lambda p: p.type == Type.ITEM_USED)
    event_data: (
        Achievement
        | Interaction
        | PortalCreated
        | PortalUsed
        | MobKilled
        | CauldronUsed
        | PlayerDied
        | BossKilled
        | SlashCommand
        | MobBorn
        | POICauldronUsed
        | ComposterUsed
        | BellUsed
        | ActorDefinition
        | RaidUpdate
        | TargetBlockHit
        | PiglinBarter
        | PlayerWaxedOrUnwaxedCopper
        | CodeBuilderRuntimeAction
        | CodeBuilderScoreboard
        | ItemUsed
        | Empty
    ) = field(since=898)
