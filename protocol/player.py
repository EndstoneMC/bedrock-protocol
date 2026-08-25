from enum import IntEnum

from protocol import int32, packet, uint8, uvarint64, varint32
from protocol.actor import ActorRuntimeID
from protocol.attributes import DimensionType
from protocol.common import BlockPos, Vec3

package = "bedrock.protocol"


class PlayerRespawnState(IntEnum, uint8):
    SEARCHING_FOR_SPAWN = 0
    READY_TO_SPAWN = 1
    CLIENT_READY_TO_SPAWN = 2


@packet(id=45, since=2168)
class RespawnPacket:
    pos: Vec3
    state: PlayerRespawnState
    runtime_id: ActorRuntimeID


class ActorDamageCause(IntEnum):
    NONE = -1
    OVERRIDE = 0
    CONTACT = 1
    ENTITY_ATTACK = 2
    PROJECTILE = 3
    SUFFOCATION = 4
    FALL = 5
    FIRE = 6
    FIRE_TICK = 7
    LAVA = 8
    DROWNING = 9
    BLOCK_EXPLOSION = 10
    ENTITY_EXPLOSION = 11
    VOID = 12
    SELF_DESTRUCT = 13
    MAGIC = 14
    WITHER = 15
    STARVE = 16
    ANVIL = 17
    THORNS = 18
    FALLING_BLOCK = 19
    PISTON = 20
    FLY_INTO_WALL = 21
    MAGMA = 22
    FIREWORKS = 23
    LIGHTNING = 24
    CHARGING = 25
    TEMPERATURE = 26
    FREEZING = 27
    STALACTITE = 28
    STALAGMITE = 29
    RAM_ATTACK = 30
    SONIC_BOOM = 31
    CAMPFIRE = 32
    SOUL_CAMPFIRE = 33
    MACE_SMASH = 34
    ALL = 35


@packet(id=38, since=2168)
class HurtArmorPacket:
    cause: ActorDamageCause
    dmg: varint32
    armor_slots: uvarint64


@packet(id=42, since=2168)
class SetHealthPacket:
    health: varint32


@packet(id=309, since=2168)
class AwardAchievementPacket:
    achievement_id: int32


@packet(id=33, since=2168)
class InteractPacket:
    class Action(IntEnum, uint8):
        INVALID = 0
        STOP_RIDING = 3
        INTERACT_UPDATE = 4
        NPC_OPEN = 5
        OPEN_INVENTORY = 6

    action: Action
    target_id: ActorRuntimeID
    pos: Vec3 | None


class SpawnPositionType(IntEnum):
    PLAYER_RESPAWN = 0
    WORLD_SPAWN = 1


@packet(id=43, since=2168)
class SetSpawnPositionPacket:
    spawn_pos_type: SpawnPositionType
    pos: BlockPos
    dimension_type: DimensionType
    spawn_block_pos: BlockPos


@packet(id=113, since=2168)
class SetLocalPlayerAsInitializedPacket:
    player_id: ActorRuntimeID
