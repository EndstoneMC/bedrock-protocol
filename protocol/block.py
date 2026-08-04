from protocol import field, int32, packet, uint8
from protocol.common import BlockPos

package = "bedrock.protocol"


@packet(id=141)
class AnvilDamagePacket:
    damage: int32 = field(type=uint8, until=2168)
    position: BlockPos
