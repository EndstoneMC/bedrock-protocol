from enum import IntEnum

from protocol import int8, int16, packet, type, uint8, uvarint32, uvarint64, varint32, varint64
from protocol.common import BlockPos, Vec2, Vec3
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


type ActorUniqueID = varint64
type ActorRuntimeID = uvarint64
type PlayerInputTick = uvarint64


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
class ActorType(IntEnum, int):
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
class ActorType(IntEnum, int):
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
