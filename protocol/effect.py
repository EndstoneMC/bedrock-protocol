"""Status and movement effects applied to an actor: world/effect/."""

from enum import IntEnum, auto

from protocol import packet, uint8, value, varint32
from protocol.actor import ActorRuntimeID, PlayerInputTick

package = "bedrock.protocol"


class MovementEffectType(IntEnum):
    INVALID = -1
    GLIDE_BOOST = 0
    DOLPHIN_BOOST = 1
    GEYSER_BOOST = value(2, since=1001)
    COUNT = auto()


@packet(id=28, since=2168)
class MobEffectPacket:
    class Event(IntEnum, uint8):
        INVALID = 0
        ADD = 1
        UPDATE = 2
        REMOVE = 3

    runtime_id: ActorRuntimeID
    event_id: Event
    effect_id: varint32
    effect_amplifier: varint32
    show_particles: bool
    effect_duration_ticks: varint32
    tick: PlayerInputTick
    ambient: bool


@packet(id=318, since=2168)
class MovementEffectPacket:
    target_runtime_id: ActorRuntimeID
    effect_id: MovementEffectType
    effect_duration: varint32
    tick: PlayerInputTick
