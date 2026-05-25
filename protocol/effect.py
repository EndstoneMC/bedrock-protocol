from enum import IntEnum

from protocol import field, int64, packet, uint8, uvarint32, uvarint64, varint32
from protocol.actor import ActorRuntimeID

package = "bedrock.protocol"


@packet(id=28)
class MobEffectPacket:
    """At the start of the game the server sends any mob effects with _sendAdditionalLevelData() if the joining player saved out with them, and then anytime a mob effect is added, removed, or updated this packet is sent."""

    class Event(IntEnum):
        INVALID = 0
        ADD = 1
        UPDATE = 2
        REMOVE = 3

    runtime_id: ActorRuntimeID
    event_id: Event = field(type=uint8)
    effect_id: varint32
    effect_amplifier: varint32
    show_particles: bool
    effect_duration_ticks: varint32
    tick: int64 = field(since=662, until=748)
    tick: uvarint64 = field(since=748)
    ambient: bool = field(since=897)


class MovementEffectType(IntEnum):
    INVALID = -1
    GLIDE_BOOST = 0
    DOLPHIN_BOOST = 1


@packet(id=318, since=748)
class MovementEffectPacket:
    """These packets are sent to the client to update specific MovementEffects."""

    runtime_id: ActorRuntimeID
    effect_type: MovementEffectType = field(type=uvarint32)
    effect_duration: varint32
    tick: uvarint64
