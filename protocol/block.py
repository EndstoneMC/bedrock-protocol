from protocol import field, int32, packet, uint8, uvarint32, varint32
from protocol.common import BlockPos

package = "bedrock.protocol"


@packet(id=141)
class AnvilDamagePacket:
    damage: int32 = field(type=uint8, until=2168)
    position: BlockPos


@packet(id=21, since=2168)
class UpdateBlockPacket:
    pos: BlockPos
    runtime_id: uvarint32
    update_flags: uint8 = field(type=uvarint32)
    layer: uvarint32


@packet(id=26, since=2168)
class BlockEventPacket:
    pos: BlockPos
    b0: varint32
    b1: varint32
