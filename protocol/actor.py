from enum import IntEnum

from protocol._dsl import field, packet, value
from protocol._primitives import float32, uint8, uvarint64, varint32

package = "bedrock.protocol"

type ActorRuntimeID = uvarint64


class ActorEvent(IntEnum):
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
    LANDED_ON_GROUND = value(75, until=622)
    ACTOR_GROW_UP = 76
    VIBRATION_DETECTED = 77
    DRINK_MILK = 78
    SHAKE_WETNESS_STOP = value(79, since=859)
    KINETIC_DAMAGE_DEALT = value(80, since=897)
    HURT_WITHOUT_RECEIVING_DAMAGE = value(81, since=975)


class Vec3:
    x: float32
    y: float32
    z: float32


@packet(id=27)
class ActorEventPacket:
    """Server-to-client signal that plays an actor event on a specific entity."""

    target_runtime_id: ActorRuntimeID
    event_id: ActorEvent = field(type=uint8)
    data: varint32
    fire_at_position: Vec3 | None = field(since=975)
