from protocol import packet, uint8, uint32, varint32
from protocol.actor import ActorUniqueID
from protocol.common import Vec3
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


@packet(id=130, since=2168)
class OnScreenTextureAnimationPacket:
    effect_id: uint32


@packet(id=25, since=2168)
class LevelEventPacket:
    event_id: varint32
    pos: Vec3
    data: varint32


@packet(id=124, since=2168)
class LevelEventGenericPacket:
    event_id: varint32
    data: CompoundTag


@packet(id=118, since=2168)
class SpawnParticleEffectPacket:
    vanilla_dimension_id: uint8
    actor_id: ActorUniqueID
    pos: Vec3
    effect_name: str
    molang_variables: str | None
