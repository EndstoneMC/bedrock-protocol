"""The actor as a subject: id aliases, links, events, synched data, the ActorType
registry, and the packets that spawn, move, remove and animate one. world/actor/.
Not the player -- world/actor/player/ is player.py."""

from enum import Enum, IntEnum, auto

from protocol import (
    field,
    int8,
    int16,
    int32,
    int64,
    packet,
    type,
    uint8,
    uint64,
    uvarint32,
    uvarint64,
    value,
    varint32,
    varint64,
)
from protocol.common import BlockPos, Vec2, Vec3
from protocol.item import NetworkItemStackDescriptor, SerializedNetworkItemStackDescriptor
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


type ActorUniqueID = varint64
type ActorRuntimeID = uvarint64
type PlayerInputTick = uvarint64


class ActorFlags(IntEnum):
    ONFIRE = 0
    SNEAKING = 1
    RIDING = 2
    SPRINTING = 3
    USINGITEM = 4
    INVISIBLE = 5
    TEMPTED = 6
    INLOVE = 7
    SADDLED = 8
    POWERED = 9
    IGNITED = 10
    BABY = 11
    CONVERTING = 12
    CRITICAL = 13
    CAN_SHOW_NAME = 14
    ALWAYS_SHOW_NAME = 15
    NOAI = 16
    SILENT = 17
    WALLCLIMBING = 18
    CANCLIMB = 19
    CANSWIM = 20
    CANFLY = 21
    CANWALK = 22
    RESTING = 23
    SITTING = 24
    ANGRY = 25
    INTERESTED = 26
    CHARGED = 27
    TAMED = 28
    ORPHANED = 29
    LEASHED = 30
    SHEARED = 31
    GLIDING = 32
    ELDER = 33
    MOVING = 34
    BREATHING = 35
    CHESTED = 36
    STACKABLE = 37
    SHOW_BOTTOM = 38
    STANDING = 39
    SHAKING = 40
    IDLING = 41
    CASTING = 42
    CHARGING = 43
    WASD_CONTROLLED = 44
    CAN_POWER_JUMP = 45
    CAN_DASH = 46
    LINGERING = 47
    HAS_COLLISION = 48
    HAS_GRAVITY = 49
    FIRE_IMMUNE = 50
    DANCING = 51
    ENCHANTED = 52
    RETURNTRIDENT = 53
    CONTAINER_IS_PRIVATE = 54
    IS_TRANSFORMING = 55
    DAMAGENEARBYMOBS = 56
    SWIMMING = 57
    BRIBED = 58
    IS_PREGNANT = 59
    LAYING_EGG = 60
    PASSENGER_CAN_PICK = 61
    TRANSITION_SITTING = 62
    EATING = 63
    LAYING_DOWN = 64
    SNEEZING = 65
    TRUSTING = 66
    ROLLING = 67
    SCARED = 68
    IN_SCAFFOLDING = 69
    OVER_SCAFFOLDING = 70
    DESCEND_THROUGH_BLOCK = 71
    BLOCKING = 72
    TRANSITION_BLOCKING = 73
    BLOCKED_USING_SHIELD = 74
    BLOCKED_USING_DAMAGED_SHIELD = 75
    SLEEPING = 76
    WANTS_TO_WAKE = 77
    TRADE_INTEREST = 78
    DOOR_BREAKER = 79
    BREAKING_OBSTRUCTION = 80
    DOOR_OPENER = 81
    IS_ILLAGER_CAPTAIN = 82
    STUNNED = 83
    ROARING = 84
    DELAYED_ATTACK = 85
    IS_AVOIDING_MOBS = 86
    IS_AVOIDING_BLOCK = 87
    FACING_TARGET_TO_RANGE_ATTACK = 88
    HIDDEN_WHEN_INVISIBLE = 89
    IS_IN_UI = 90
    STALKING = 91
    EMOTING = 92
    CELEBRATING = 93
    ADMIRING = 94
    CELEBRATING_SPECIAL = 95
    OUT_OF_CONTROL = 96
    RAM_ATTACK = 97
    PLAYING_DEAD = 98
    IN_ASCENDABLE_BLOCK = 99
    OVER_DESCENDABLE_BLOCK = 100
    CROAKING = 101
    EAT_MOB = 102
    JUMP_GOAL_JUMP = 103
    EMERGING = 104
    SNIFFING = 105
    DIGGING = 106
    SONIC_BOOM = 107
    HAS_DASH_COOLDOWN = 108
    PUSH_TOWARDS_CLOSEST_SPACE = 109
    DEPRECATED_1 = 110
    DEPRECATED_2 = 111
    DEPRECATED_3 = 112
    SEARCHING = 113
    CRAWLING = 114
    TIMER_FLAG_1 = 115
    TIMER_FLAG_2 = 116
    TIMER_FLAG_3 = 117
    BODY_ROTATION_BLOCKED = 118
    RENDERS_WHEN_INVISIBLE = 119
    ROTATION_AXIS_ALIGNED = 120
    COLLIDABLE = 121
    WASD_FREE_CAMERA_CONTROLLED = 122
    DOES_SERVER_AUTH_ONLY_DISMOUNT = 123
    BODY_ROTATION_ALWAYS_FOLLOWS_HEAD = 124
    CAN_USE_VERTICAL_MOVEMENT_ACTION = 125
    ROTATION_LOCKED_TO_VEHICLE = 126
    USES_LEGACY_FRICTION = value(127, since=975)
    USES_UNIFORM_AIR_DRAG = value(128, since=975)
    NAMEPLATE_DEPTH_TESTED = value(129, since=975)
    NOT_PICKABLE_FROM_INSIDE = value(130, since=2168)
    COUNT = auto()


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
    RESERVED_139 = value(139, since=975)
    NAMEPLATE_RENDER_DISTANCE_MAX = value(140, since=975)
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


class DataItemBytePayload:
    type: DataItemType = field(since=2168)
    value: int8


class DataItemShortPayload:
    type: DataItemType = field(since=2168)
    value: int16


class DataItemIntPayload:
    type: DataItemType = field(since=2168)
    value: varint32


class DataItemFloatPayload:
    type: DataItemType = field(since=2168)
    value: float


class DataItemStringPayload:
    type: DataItemType = field(since=2168)
    value: str


class DataItemCompoundTagPayload:
    type: DataItemType = field(since=2168)
    value: CompoundTag


class DataItemPosPayload:
    type: DataItemType = field(since=2168)
    value: BlockPos


class DataItemInt64Payload:
    type: DataItemType = field(since=2168)
    value: varint64


class DataItemVec3Payload:
    type: DataItemType = field(since=2168)
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
    MINECART_TNT = value(524385, cpp_name="MinecartTNT")
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
    SULFUR_CUBE = value(2969, since=975)


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
    MINECART_TNT = value(524385, cpp_name="MinecartTNT")
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


@packet(id=14)
class RemoveActorPacket:
    entity_id: ActorUniqueID


@packet(id=35)
class ActorPickRequestPacket:
    id: int64
    max_slots: uint8
    with_data: bool


@packet(id=89)
class AddBehaviorTreePacket:
    json_input: str


@packet(id=17)
class TakeItemActorPacket:
    item_id: ActorRuntimeID
    actor_id: ActorRuntimeID


class MoveActorAbsoluteData:
    runtime_id: ActorRuntimeID
    header: uint8
    pos: Vec3
    rot_x: uint8
    rot_y: uint8
    rot_y_head: uint8


@packet(id=18)
class MoveActorAbsolutePacket:
    move_data: MoveActorAbsoluteData


@packet(id=22)
class AddPaintingPacket:
    entity_id: ActorUniqueID
    runtime_id: ActorRuntimeID
    pos: Vec3
    dir: varint32
    motif: str


class ActorEvent(IntEnum, uint8):
    NONE = 0
    JUMP = 1
    HURT = 2
    DEATH = 3
    START_ATTACKING = 4
    STOP_ATTACKING = 5
    TAMING_FAILED = 6
    TAMING_SUCCEEDED = 7
    SHAKE_WETNESS = 8
    EAT_GRASS = 10
    FISHHOOK_BUBBLE = 11
    FISHHOOK_FISHPOS = 12
    FISHHOOK_HOOKTIME = 13
    FISHHOOK_TEASE = 14
    SQUID_FLEEING = 15
    ZOMBIE_CONVERTING = 16
    PLAY_AMBIENT = 17
    SPAWN_ALIVE = 18
    START_OFFER_FLOWER = 19
    STOP_OFFER_FLOWER = 20
    LOVE_HEARTS = 21
    VILLAGER_ANGRY = 22
    VILLAGER_HAPPY = 23
    WITCH_HAT_MAGIC = 24
    FIREWORKS_EXPLODE = 25
    IN_LOVE_HEARTS = 26
    SILVERFISH_MERGE_ANIM = 27
    GUARDIAN_ATTACK_SOUND = 28
    DRINK_POTION = 29
    THROW_POTION = 30
    PRIME_TNTCART = 31
    PRIME_CREEPER = 32
    AIR_SUPPLY = 33
    DEPRECATED_ADD_PLAYER_LEVELS = 34
    GUARDIAN_MINING_FATIGUE = 35
    AGENT_SWING_ARM = 36
    DRAGON_START_DEATH_ANIM = 37
    GROUND_DUST = 38
    SHAKE = 39
    FEED = 57
    BABY_AGE = 60
    INSTANT_DEATH = 61
    NOTIFY_TRADE = 62
    LEASH_DESTROYED = 63
    CARAVAN_UPDATED = 64
    TALISMAN_ACTIVATE = 65
    DEPRECATED_UPDATE_STRUCTURE_FEATURE = 66
    PLAYER_SPAWNED_MOB = 67
    PUKE = 68
    UPDATE_STACK_SIZE = 69
    START_SWIMMING = 70
    BALLOON_POP = 71
    TREASURE_HUNT = 72
    SUMMON_AGENT = 73
    FINISHED_CHARGING_ITEM = 74
    ACTOR_GROW_UP = 76
    VIBRATION_DETECTED = 77
    DRINK_MILK = 78
    SHAKE_WETNESS_STOP = 79
    KINETIC_DAMAGE_DEALT = 80
    HURT_WITHOUT_RECEIVING_DAMAGE = value(81, since=975)


@packet(id=27)
class ActorEventPacket:
    runtime_id: ActorRuntimeID
    event_id: ActorEvent
    data: varint32
    fire_at_position: Vec3 | None = field(since=975)


@packet(id=40)
class SetActorMotionPacket:
    runtime_id: ActorRuntimeID
    motion: Vec3
    tick: PlayerInputTick


@packet(id=41)
class SetActorLinkPacket:
    link: ActorLink


class ActorSwingSource(Enum, uint8):
    NONE = 0
    BUILD = 1
    MINE = 2
    INTERACT = 3
    ATTACK = 4
    USE_ITEM = 5
    THROW_ITEM = 6
    DROP_ITEM = 7
    EVENT = 8


@packet(id=44)
class AnimatePacket:
    class Action(IntEnum, uint8):
        NO_ACTION = 0
        SWING = 1
        WAKE_UP = 3
        CRITICAL_HIT = 4
        MAGIC_CRITICAL_HIT = 5

    action: Action
    runtime_id: ActorRuntimeID
    data: float
    swing_source: ActorSwingSource | None = field(type=str)


@packet(id=66)
class SpawnExperienceOrbPacket:
    pos: Vec3
    xp_value: varint32


@packet(id=119)
class AvailableActorIdentifiersPacket:
    identifier_list: CompoundTag


@packet(id=157)
class MotionPredictionHintsPacket:
    runtime_id: ActorRuntimeID
    motion: Vec3
    on_ground: bool


@packet(id=189)
class DeathInfoPacket:
    death_cause_attack_name: str
    death_cause_message_list: list[str]


@packet(id=165)
class SyncActorPropertyPacket:
    property_data: CompoundTag


@packet(id=182)
class ChangeMobPropertyPacket:
    actor_id: ActorUniqueID
    prop_name: str
    bool_component_val: bool
    string_component_val: str
    int_component_val: varint32
    float_component_val: float


@packet(id=158)
class AnimateEntityPacket:
    animation: str
    next_state: str
    stop_expression: str
    stop_expression_version: int32
    controller: str
    blend_out_time: float
    runtime_ids: list[ActorRuntimeID]


@packet(id=98)
class NpcRequestPacket:
    class RequestType(IntEnum, uint8):
        SET_ACTIONS = 0
        EXECUTE_ACTION = 1
        EXECUTE_CLOSING_COMMANDS = 2
        SET_NAME = 3
        SET_SKIN = 4
        SET_INTERACT_TEXT = 5
        EXECUTE_OPENING_COMMANDS = 6

    id: ActorRuntimeID
    type: RequestType
    actions: str
    action_index: uint8
    scene_name: str


@packet(id=169)
class NpcDialoguePacket:
    class NpcDialogueActionType(IntEnum):
        OPEN = 0
        CLOSE = 1

    npc_id: ActorUniqueID = field(type=uint64)
    npc_dialogue_action_type: NpcDialogueActionType
    dialogue: str
    scene_name: str
    npc_name: str
    action_json: str


@packet(id=15, until=2168)
class AddItemActorPacket:
    id: ActorUniqueID
    runtime_id: ActorRuntimeID
    item: NetworkItemStackDescriptor
    pos: Vec3
    velocity: Vec3
    data: SynchedActorData.CopyableDataList
    is_from_fishing: bool


@packet(id=15, since=2168)
class AddItemActorPacket:
    id: ActorUniqueID
    runtime_id: ActorRuntimeID
    item: SerializedNetworkItemStackDescriptor
    pos: Vec3
    velocity: Vec3
    data: SynchedActorData.CopyableDataList
    is_from_fishing: bool
