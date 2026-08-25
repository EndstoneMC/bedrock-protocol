from enum import IntEnum

from protocol import field, int32, packet, uint8, uint32, uvarint32, uvarint64, varint32
from protocol.actor import ActorUniqueID
from protocol.common import BlockPos
from protocol.nbt import CompoundTag

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


@packet(id=34, since=2168)
class BlockPickRequestPacket:
    pos: BlockPos
    with_data: bool
    max_slots: uint8


@packet(id=56, since=2168)
class BlockActorDataPacket:
    pos: BlockPos
    data: CompoundTag


class ActorBlockSyncMessage:
    class MessageId(IntEnum, uint32):
        NONE = 0
        CREATE = 1
        DESTROY = 2


@packet(id=110, since=2168)
class UpdateBlockSyncedPacket:
    pos: BlockPos
    runtime_id: uvarint32
    update_flags: uint8 = field(type=uvarint32)
    layer: uvarint32
    entity_unique_id: ActorUniqueID = field(type=uvarint64)
    message: ActorBlockSyncMessage.MessageId = field(type=uvarint64)
