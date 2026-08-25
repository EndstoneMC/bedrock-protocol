from enum import IntEnum, auto

from protocol import int8, int16, int64, packet, type, uint8, uvarint32, uvarint64, varint32, varint64
from protocol.common import BlockPos, Vec2, Vec3
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


type ActorUniqueID = varint64
type ActorRuntimeID = uvarint64
type PlayerInputTick = uvarint64


class ActorDataIDs(IntEnum, uint8):
    RESERVED_0 = 0
    STRUCTURAL_INTEGRITY = 1
    VARIANT = 2
    COLOR_INDEX = 3
    NAME = 4
    OWNER = 5
    TARGET = 6
    AIR_SUPPLY = 7
    EFFECT_COLOR = 8
    RESERVED_009 = 9
    RESERVED_010 = 10
    HURT = 11
    HURT_DIR = 12
    ROW_TIME_LEFT = 13
    ROW_TIME_RIGHT = 14
    VALUE = 15
    DISPLAY_TILE_RUNTIME_ID = 16
    DISPLAY_OFFSET = 17
    CUSTOM_DISPLAY = 18
    SWELL = 19
    OLD_SWELL = 20
    SWELL_DIR = 21
    CHARGE_AMOUNT = 22
    DEPRECATED_CARRY_BLOCK_RUNTIME_ID = 23
    CLIENT_EVENT = 24
    USING_ITEM = 25
    PLAYER_FLAGS = 26
    PLAYER_INDEX = 27
    BED_POSITION = 28
    X_POWER = 29
    Y_POWER = 30
    Z_POWER = 31
    AUX_POWER = 32
    FISHX = 33
    FISHZ = 34
    FISHANGLE = 35
    AUX_VALUE_DATA = 36
    LEASH_HOLDER = 37
    RESERVED_038 = 38
    HAS_NPC = 39
    NPC_DATA = 40
    ACTIONS = 41
    AIR_SUPPLY_MAX = 42
    MARK_VARIANT = 43
    CONTAINER_TYPE = 44
    CONTAINER_SIZE = 45
    CONTAINER_STRENGTH_MODIFIER = 46
    BLOCK_TARGET = 47
    INV = 48
    TARGET_A = 49
    TARGET_B = 50
    TARGET_C = 51
    AERIAL_ATTACK = 52
    RESERVED_053 = 53
    RESERVED_054 = 54
    FUSE_TIME = 55
    RESERVED_056 = 56
    SEAT_LOCK_PASSENGER_ROTATION = 57
    SEAT_LOCK_PASSENGER_ROTATION_DEGREES = 58
    SEAT_ROTATION_OFFSET = 59
    SEAT_ROTATION_OFFSET_DEGREES = 60
    DATA_RADIUS = 61
    DATA_WAITING = 62
    DATA_PARTICLE = 63
    PEEK_ID = 64
    ATTACH_FACE = 65
    ATTACHED = 66
    ATTACH_POS = 67
    TRADE_TARGET = 68
    CAREER = 69
    HAS_COMMAND_BLOCK = 70
    COMMAND_NAME = 71
    LAST_COMMAND_OUTPUT = 72
    TRACK_COMMAND_OUTPUT = 73
    RESERVED_074 = 74
    STRENGTH = 75
    STRENGTH_MAX = 76
    DATA_SPELL_CASTING_COLOR = 77
    DATA_LIFETIME_TICKS = 78
    POSE_INDEX = 79
    DATA_TICK_OFFSET = 80
    NAMETAG_ALWAYS_SHOW = 81
    COLOR_2_INDEX = 82
    NAME_AUTHOR = 83
    SCORE = 84
    BALLOON_ANCHOR = 85
    PUFFED_STATE = 86
    BUBBLE_TIME = 87
    AGENT = 88
    SITTING_AMOUNT = 89
    SITTING_AMOUNT_PREVIOUS = 90
    EATING_COUNTER = 91
    RESERVED_092 = 92
    LAYING_AMOUNT = 93
    LAYING_AMOUNT_PREVIOUS = 94
    DATA_DURATION = 95
    DATA_SPAWN_TIME_DEPRECATED = 96
    DATA_CHANGE_RATE = 97
    DATA_CHANGE_ON_PICKUP = 98
    DATA_PICKUP_COUNT = 99
    INTERACT_TEXT = 100
    TRADE_TIER = 101
    MAX_TRADE_TIER = 102
    TRADE_EXPERIENCE = 103
    SKIN_ID = 104
    SPAWNING_FRAMES = 105
    COMMAND_BLOCK_TICK_DELAY = 106
    COMMAND_BLOCK_EXECUTE_ON_FIRST_TICK = 107
    AMBIENT_SOUND_INTERVAL = 108
    AMBIENT_SOUND_INTERVAL_RANGE = 109
    AMBIENT_SOUND_EVENT_NAME = 110
    FALL_DAMAGE_MULTIPLIER = 111
    NAME_RAW_TEXT = 112
    CAN_RIDE_TARGET = 113
    LOW_TIER_CURED_TRADE_DISCOUNT = 114
    HIGH_TIER_CURED_TRADE_DISCOUNT = 115
    NEARBY_CURED_TRADE_DISCOUNT = 116
    NEARBY_CURED_DISCOUNT_TIME_STAMP = 117
    HITBOX = 118
    IS_BUOYANT = 119
    FREEZING_EFFECT_STRENGTH = 120
    BUOYANCY_DATA = 121
    GOAT_HORN_COUNT = 122
    BASE_RUNTIME_ID = 123
    MOVEMENT_SOUND_DISTANCE_OFFSET = 124
    HEARTBEAT_INTERVAL_TICKS = 125
    HEARTBEAT_SOUND_EVENT = 126
    PLAYER_LAST_DEATH_POS = 127
    PLAYER_LAST_DEATH_DIMENSION = 128
    PLAYER_HAS_DIED = 129
    COLLISION_BOX = 130
    VISIBLE_MOB_EFFECTS = 131
    FILTERED_NAME = 132
    ENTER_BED_POSITION = 133
    SEAT_THIRD_PERSON_CAMERA_RADIUS = 134
    SEAT_CAMERA_RELAX_DISTANCE_SMOOTHING = 135
    AIM_ASSIST_PRIORITY_PRESET_ID = 136
    AIM_ASSIST_PRIORITY_CATEGORY_ID = 137
    AIM_ASSIST_PRIORITY_ACTOR_ID = 138
    RESERVED_139 = 139
    NAMEPLATE_RENDER_DISTANCE_MAX = 140
    COUNT = auto()


class DataItemType(IntEnum, uint8):
    BYTE = 0
    SHORT = 1
    INT = 2
    FLOAT = 3
    STRING = 4
    COMPOUND_TAG = 5
    POS = 6
    INT64 = 7
    VEC3 = 8
    UNKNOWN = 9


@type(until=2168)
class DataItemBytePayload:
    value: int8


@type(since=2168)
class DataItemBytePayload:
    type: DataItemType
    value: int8


@type(until=2168)
class DataItemShortPayload:
    value: int16


@type(since=2168)
class DataItemShortPayload:
    type: DataItemType
    value: int16


@type(until=2168)
class DataItemIntPayload:
    value: varint32


@type(since=2168)
class DataItemIntPayload:
    type: DataItemType
    value: varint32


@type(until=2168)
class DataItemFloatPayload:
    value: float


@type(since=2168)
class DataItemFloatPayload:
    type: DataItemType
    value: float


@type(until=2168)
class DataItemStringPayload:
    value: str


@type(since=2168)
class DataItemStringPayload:
    type: DataItemType
    value: str


@type(until=2168)
class DataItemCompoundTagPayload:
    value: CompoundTag


@type(since=2168)
class DataItemCompoundTagPayload:
    type: DataItemType
    value: CompoundTag


@type(until=2168)
class DataItemPosPayload:
    value: BlockPos


@type(since=2168)
class DataItemPosPayload:
    type: DataItemType
    value: BlockPos


@type(until=2168)
class DataItemInt64Payload:
    value: varint64


@type(since=2168)
class DataItemInt64Payload:
    type: DataItemType
    value: varint64


@type(until=2168)
class DataItemVec3Payload:
    value: Vec3


@type(since=2168)
class DataItemVec3Payload:
    type: DataItemType
    value: Vec3


class DataItemEntry:
    id: uvarint32
    payload: (
        DataItemBytePayload
        | DataItemShortPayload
        | DataItemIntPayload
        | DataItemFloatPayload
        | DataItemStringPayload
        | DataItemCompoundTagPayload
        | DataItemPosPayload
        | DataItemInt64Payload
        | DataItemVec3Payload
    )


class SynchedActorData:
    class CopyableDataList:
        data: list[DataItemEntry]


class PropertySyncData:
    class PropertySyncIntEntry:
        property_index: uvarint32
        data: varint32

    class PropertySyncFloatEntry:
        property_index: uvarint32
        data: float

    int_entries: list[PropertySyncIntEntry]
    float_entries: list[PropertySyncFloatEntry]


class SyncedAttribute:
    name: str
    min_value: float
    current_value: float
    max_value: float


class ActorLinkType(IntEnum, uint8):
    NONE = 0
    RIDING = 1
    PASSENGER = 2


class ActorLink:
    a: ActorUniqueID
    b: ActorUniqueID
    type: ActorLinkType
    immediate: bool
    passenger_initiated: bool
    vehicle_angular_velocity: float


@packet(id=13)
class AddActorPacket:
    entity_id: ActorUniqueID
    runtime_id: ActorRuntimeID
    actor_type: str
    pos: Vec3
    velocity: Vec3
    rot: Vec2
    y_head_rotation: float
    y_body_rotation: float
    attributes: list[SyncedAttribute]
    data: SynchedActorData.CopyableDataList
    synched_properties: PropertySyncData
    links: list[ActorLink]


@packet(id=39)
class SetActorDataPacket:
    id: ActorRuntimeID
    packed_items: SynchedActorData.CopyableDataList
    synched_properties: PropertySyncData
    tick: PlayerInputTick


@type(until=2168)
class ActorType(IntEnum):
    UNDEFINED = 1
    TYPE_MASK = 255
    MOB = 256
    PATHFINDER_MOB = 768
    MONSTER = 2816
    ANIMAL = 4864
    TAMABLE_ANIMAL = 21248
    AMBIENT = 33024
    UNDEAD = 65792
    UNDEAD_MONSTER = 68352
    ZOMBIE_MONSTER = 199424
    ARTHROPOD = 264960
    MINECART = 524288
    SKELETON_MONSTER = 1116928
    EQUINE_ANIMAL = 2118400
    PROJECTILE = 4194304
    ABSTRACT_ARROW = 8388608
    WATER_ANIMAL = 8960
    VILLAGER_BASE = 16777984
    CHICKEN = 4874
    COW = 4875
    PIG = 4876
    SHEEP = 4877
    WOLF = 21262
    VILLAGER = 16777999
    MUSHROOM_COW = 4880
    SQUID = 8977
    RABBIT = 4882
    BAT = 33043
    IRON_GOLEM = 788
    SNOW_GOLEM = 789
    OCELOT = 21270
    HORSE = 2118423
    POLAR_BEAR = 4892
    LLAMA = 4893
    PARROT = 21278
    DOLPHIN = 8991
    DONKEY = 2118424
    MULE = 2118425
    SKELETON_HORSE = 2183962
    ZOMBIE_HORSE = 2183963
    ZOMBIE = 199456
    CREEPER = 2849
    SKELETON = 1116962
    SPIDER = 264995
    PIG_ZOMBIE = 68388
    SLIME = 2853
    ENDER_MAN = 2854
    SILVERFISH = 264999
    CAVE_SPIDER = 265000
    GHAST = 2857
    LAVA_SLIME = 2858
    BLAZE = 2859
    ZOMBIE_VILLAGER = 199468
    WITCH = 2861
    STRAY = 1116974
    HUSK = 199471
    WITHER_SKELETON = 1116976
    GUARDIAN = 2865
    ELDER_GUARDIAN = 2866
    NPC = 307
    WITHER_BOSS = 68404
    DRAGON = 2869
    SHULKER = 2870
    ENDERMITE = 265015
    AGENT = 312
    VINDICATOR = 2873
    PHANTOM = 68410
    ILLAGER_BEAST = 2875
    ARMOR_STAND = 317
    TRIPOD_CAMERA = 318
    PLAYER = 319
    ITEM_ENTITY = 64
    PRIMED_TNT = 65
    FALLING_BLOCK = 66
    MOVING_BLOCK = 67
    EXPERIENCE_POTION = 4194372
    EXPERIENCE = 69
    EYE_OF_ENDER = 70
    ENDER_CRYSTAL = 71
    FIREWORKS_ROCKET = 72
    TRIDENT = 12582985
    TURTLE = 4938
    CAT = 21323
    SHULKER_BULLET = 4194380
    FISHING_HOOK = 77
    CHALKBOARD = 78
    DRAGON_FIREBALL = 4194383
    ARROW = 12582992
    SNOWBALL = 4194385
    THROWN_EGG = 4194386
    PAINTING = 83
    LARGE_FIREBALL = 4194389
    THROWN_POTION = 4194390
    ENDERPEARL = 4194391
    LEASH_KNOT = 88
    WITHER_SKULL = 4194393
    BOAT_RIDEABLE = 90
    WITHER_SKULL_DANGEROUS = 4194395
    LIGHTNING_BOLT = 93
    SMALL_FIREBALL = 4194398
    AREA_EFFECT_CLOUD = 95
    LINGERING_POTION = 4194405
    LLAMA_SPIT = 4194406
    EVOCATION_FANG = 4194407
    EVOCATION_ILLAGER = 2920
    VEX = 2921
    MINECART_RIDEABLE = 524372
    MINECART_HOPPER = 524384
    MINECART_TNT = 524385
    MINECART_CHEST = 524386
    MINECART_FURNACE = 524387
    MINECART_COMMAND_BLOCK = 524388
    ICE_BOMB = 4194410
    BALLOON = 107
    PUFFERFISH = 9068
    SALMON = 9069
    DROWNED = 199534
    TROPICALFISH = 9071
    FISH = 9072
    PANDA = 4977
    PILLAGER = 2930
    VILLAGER_V2 = 16778099
    ZOMBIE_VILLAGER_V2 = 199540
    SHIELD = 117
    WANDERING_TRADER = 886
    LECTERN = 119
    ELDER_GUARDIAN_GHOST = 2936
    FOX = 4985
    BEE = 378
    PIGLIN = 379
    HOGLIN = 4988
    STRIDER = 4989
    ZOGLIN = 68478
    PIGLIN_BRUTE = 383
    GOAT = 4992
    GLOW_SQUID = 9089
    AXOLOTL = 4994
    WARDEN = 2947
    FROG = 4996
    TADPOLE = 9093
    ALLAY = 390
    CHEST_BOAT_RIDEABLE = 218
    TRADER_LLAMA = 5021
    CAMEL = 5002
    SNIFFER = 5003
    BREEZE = 2956
    BREEZE_WIND_CHARGE_PROJECTILE = 4194445
    ARMADILLO = 5006
    WIND_CHARGE_PROJECTILE = 4194447
    BOGGED = 1117072
    OMINOUS_ITEM_SPAWNER = 145
    CREAKING = 2962
    HAPPY_GHAST = 5011
    COPPER_GOLEM = 916
    NAUTILUS = 9109
    ZOMBIE_NAUTILUS = 74646
    PARCHED = 1117079
    CAMEL_HUSK = 70552
    SULFUR_CUBE = 2969


@type(since=2168)
class ActorType(IntEnum):
    UNDEFINED = 1
    TYPE_MASK = 255
    MOB = 256
    PATHFINDER_MOB = 768
    MONSTER = 2816
    ANIMAL = 4864
    TAMABLE_ANIMAL = 21248
    AMBIENT = 33024
    UNDEAD = 65792
    UNDEAD_MONSTER = 68352
    ZOMBIE_MONSTER = 199424
    ARTHROPOD = 264960
    MINECART = 524288
    SKELETON_MONSTER = 1116928
    EQUINE_ANIMAL = 2118400
    PROJECTILE = 4194304
    ABSTRACT_ARROW = 8388608
    WATER_ANIMAL = 8960
    VILLAGER_BASE = 16777984
    CHICKEN = 4874
    COW = 4875
    PIG = 4876
    SHEEP = 4877
    WOLF = 21262
    VILLAGER = 16777999
    MUSHROOM_COW = 4880
    SQUID = 8977
    RABBIT = 4882
    BAT = 33043
    IRON_GOLEM = 788
    SNOW_GOLEM = 789
    OCELOT = 21270
    HORSE = 2118423
    POLAR_BEAR = 4892
    LLAMA = 4893
    PARROT = 21278
    DOLPHIN = 8991
    DONKEY = 2118424
    MULE = 2118425
    SKELETON_HORSE = 2183962
    ZOMBIE_HORSE = 2183963
    ZOMBIE = 199456
    CREEPER = 2849
    SKELETON = 1116962
    SPIDER = 264995
    PIG_ZOMBIE = 68388
    SLIME = 2853
    ENDER_MAN = 2854
    SILVERFISH = 264999
    CAVE_SPIDER = 265000
    GHAST = 2857
    LAVA_SLIME = 2858
    BLAZE = 2859
    ZOMBIE_VILLAGER = 199468
    WITCH = 2861
    STRAY = 1116974
    HUSK = 199471
    WITHER_SKELETON = 1116976
    GUARDIAN = 2865
    ELDER_GUARDIAN = 2866
    NPC = 307
    WITHER_BOSS = 68404
    DRAGON = 2869
    SHULKER = 2870
    ENDERMITE = 265015
    AGENT = 312
    VINDICATOR = 2873
    PHANTOM = 68410
    ILLAGER_BEAST = 2875
    ARMOR_STAND = 317
    TRIPOD_CAMERA = 318
    PLAYER = 319
    ITEM_ENTITY = 64
    PRIMED_TNT = 65
    FALLING_BLOCK = 66
    MOVING_BLOCK = 67
    EXPERIENCE_POTION = 4194372
    EXPERIENCE = 69
    EYE_OF_ENDER = 70
    ENDER_CRYSTAL = 71
    FIREWORKS_ROCKET = 72
    TRIDENT = 12582985
    TURTLE = 4938
    CAT = 21323
    SHULKER_BULLET = 4194380
    FISHING_HOOK = 77
    CHALKBOARD = 78
    DRAGON_FIREBALL = 4194383
    ARROW = 12582992
    SNOWBALL = 4194385
    THROWN_EGG = 4194386
    PAINTING = 83
    LARGE_FIREBALL = 4194389
    THROWN_POTION = 4194390
    ENDERPEARL = 4194391
    LEASH_KNOT = 88
    WITHER_SKULL = 4194393
    BOAT_RIDEABLE = 90
    WITHER_SKULL_DANGEROUS = 4194395
    LIGHTNING_BOLT = 93
    SMALL_FIREBALL = 4194398
    AREA_EFFECT_CLOUD = 95
    LINGERING_POTION = 4194405
    LLAMA_SPIT = 4194406
    EVOCATION_FANG = 4194407
    EVOCATION_ILLAGER = 2920
    VEX = 2921
    MINECART_RIDEABLE = 524372
    MINECART_HOPPER = 524384
    MINECART_TNT = 524385
    MINECART_CHEST = 524386
    MINECART_FURNACE = 524387
    MINECART_COMMAND_BLOCK = 524388
    ICE_BOMB = 4194410
    BALLOON = 107
    PUFFERFISH = 9068
    SALMON = 9069
    DROWNED = 199534
    TROPICALFISH = 9071
    FISH = 9072
    PANDA = 4977
    PILLAGER = 2930
    VILLAGER_V2 = 16778099
    ZOMBIE_VILLAGER_V2 = 199540
    SHIELD = 117
    WANDERING_TRADER = 886
    LECTERN = 119
    ELDER_GUARDIAN_GHOST = 2936
    FOX = 4985
    BEE = 378
    PIGLIN = 379
    HOGLIN = 4988
    STRIDER = 4989
    ZOGLIN = 68478
    PIGLIN_BRUTE = 383
    GOAT = 4992
    GLOW_SQUID = 9089
    AXOLOTL = 4994
    WARDEN = 2947
    FROG = 4996
    TADPOLE = 9093
    ALLAY = 390
    CHEST_BOAT_RIDEABLE = 218
    TRADER_LLAMA = 5021
    CAMEL = 5002
    SNIFFER = 5003
    BREEZE = 2956
    BREEZE_WIND_CHARGE_PROJECTILE = 4194445
    ARMADILLO = 5006
    WIND_CHARGE_PROJECTILE = 4194447
    BOGGED = 1117072
    OMINOUS_ITEM_SPAWNER = 145
    CREAKING = 2962
    HAPPY_GHAST = 5011
    COPPER_GOLEM = 916
    NAUTILUS = 9109
    ZOMBIE_NAUTILUS = 74646
    PARCHED = 1117079
    CAMEL_HUSK = 70552
    SULFUR_CUBE = 921
    CUSHION = 154


@packet(id=96)
class SetLastHurtByPacket:
    last_hurt_by: ActorType


@packet(id=14, since=2168)
class RemoveActorPacket:
    entity_id: ActorUniqueID


@packet(id=35, since=2168)
class ActorPickRequestPacket:
    id: int64
    max_slots: uint8
    with_data: bool
