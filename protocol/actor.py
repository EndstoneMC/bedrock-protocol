import uuid
from enum import IntEnum

from protocol import (
    field,
    int32,
    packet,
    type,
    uint8,
    uvarint64,
    value,
    varint32,
    varint64,
)
from protocol.common import Vec3
from protocol.nbt import CompoundTag

package = "bedrock.protocol"

type ActorRuntimeID = uvarint64
type ActorUniqueID = varint64


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


@packet(id=27)
class ActorEventPacket:
    """All kinds of actor state changes (see Actor::handleEntityEvent). Ranges from
    a crossbow being ready to fire to taming animals, some of which may be obsolete
    (frex, ADD_PLAYER_LEVELS)."""

    runtime_id: ActorRuntimeID
    event_id: ActorEvent = field(type=uint8)
    data: varint32
    fire_at_position: Vec3 | None = field(since=975)


class ActorSwingSource(IntEnum):
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
    """Combination of server bound and client bound packets to trigger animations."""

    class Action(IntEnum):
        NO_ACTION = 0
        SWING = 1
        WAKE_UP = 3
        CRITICAL_HIT = 4
        MAGIC_CRITICAL_HIT = 5

    action: Action = field(type=varint32, until=897)
    action: Action = field(type=uint8, since=897)
    runtime_id: ActorRuntimeID
    data: float = field(since=859)
    swing_source: ActorSwingSource | None = field(type=str, since=897)


@packet(id=158)
class AnimateEntityPacket:
    """The AnimateEntityPacket is used to trigger a one-off animation on the client
    it is sent to."""

    animation: str
    next_state: str
    stop_expression: str
    stop_expression_version: int32 = field(since=465)
    controller: str
    blend_out_time: float
    runtime_ids: list[ActorRuntimeID]


@packet(id=152, since=407)
class EmoteListPacket:
    """Allows clients to download emotes that other clients have equipped."""

    runtime_id: ActorRuntimeID
    emote_piece_ids: list[uuid.UUID]


@packet(id=33)
class InteractPacket:
    """Used for inventory button press and in _updateInteraction() for a variety of
    purposes. From the client."""

    class Action(IntEnum):
        INVALID = 0
        STOP_RIDING = 3
        INTERACT_UPDATE = 4
        NPC_OPEN = 5
        OPEN_INVENTORY = 6

    action: Action = field(type=uint8)
    target_id: ActorRuntimeID
    pos: Vec3 = field(when=lambda p: p.action == Action.INTERACT_UPDATE, until=388)
    pos: Vec3 = field(
        when=lambda p: (
            p.action == Action.INTERACT_UPDATE or p.action == Action.STOP_RIDING
        ),
        since=388,
        until=897,
    )
    pos: Vec3 | None = field(since=897)


@type(since=544)
class AttributeModifierOperation(IntEnum):
    OPERATION_ADDITION = 0
    OPERATION_MULTIPLY_BASE = 1
    OPERATION_MULTIPLY_TOTAL = 2
    OPERATION_CAP = 3


@type(since=544)
class AttributeOperands(IntEnum):
    OPERAND_MIN = 0
    OPERAND_MAX = 1
    OPERAND_CURRENT = 2


@type(since=544)
class AttributeModifier:
    id: str
    name: str
    amount: float
    operation: AttributeModifierOperation = field(type=int32)
    operand: AttributeOperands = field(type=int32)
    serialize: bool


class AttributeData:
    min_value: float
    max_value: float
    current_value: float
    default_min_value: float = field(since=729)
    default_max_value: float = field(since=729)
    default_value: float
    name: str
    modifiers: list[AttributeModifier] = field(since=544)


@packet(id=29)
class UpdateAttributesPacket:
    runtime_id: ActorRuntimeID
    attribute_data: list[AttributeData]
    tick: uvarint64 = field(since=419)


@packet(id=119)
class AvailableActorIdentifiersPacket:
    """Sends the whole list of actor identifiers at game start from the server."""

    identifier_list: CompoundTag
