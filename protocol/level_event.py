from protocol import packet, uint32

package = "bedrock.protocol"


@packet(id=130, since=2168)
class OnScreenTextureAnimationPacket:
    effect_id: uint32
