from protocol import packet, uint32, varint32
from protocol.common import Vec3

package = "bedrock.protocol"


@packet(id=130, since=2168)
class OnScreenTextureAnimationPacket:
    effect_id: uint32


@packet(id=25, since=2168)
class LevelEventPacket:
    event_id: varint32
    pos: Vec3
    data: varint32
