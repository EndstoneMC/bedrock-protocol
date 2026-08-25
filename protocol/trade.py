from protocol import packet, varint32
from protocol.actor import ActorUniqueID
from protocol.inventory import ContainerID, ContainerType
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


@packet(id=80, since=2168)
class UpdateTradePacket:
    container_id: ContainerID
    type: ContainerType
    size: varint32
    trader_tier: varint32
    entity_unique_id: ActorUniqueID
    last_trading_player: ActorUniqueID
    display_name: str
    use_new_trade_screen: bool
    using_economy_trade: bool
    data: CompoundTag
