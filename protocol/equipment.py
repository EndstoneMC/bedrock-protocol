from protocol import field, int32, packet, uint8
from protocol.actor import ActorRuntimeID
from protocol.inventory import ContainerID, NetworkItemStackDescriptor, SerializedNetworkItemStackDescriptor

package = "bedrock.protocol"


@packet(id=31)
class MobEquipmentPacket:
    """One slot at a time, where MobArmorEquipmentPacket carries every armor slot."""

    runtime_id: ActorRuntimeID
    item: SerializedNetworkItemStackDescriptor
    slot: int32 = field(type=uint8)
    selected_slot: int32 = field(type=uint8)
    container_id: ContainerID


@packet(id=32, until=1001)
class MobArmorEquipmentPacket:
    """Every armor slot at once, where MobEquipmentPacket carries one at a time."""

    runtime_id: ActorRuntimeID
    head: NetworkItemStackDescriptor
    torso: NetworkItemStackDescriptor
    legs: NetworkItemStackDescriptor
    feet: NetworkItemStackDescriptor
    body: NetworkItemStackDescriptor


@packet(id=32, since=1001)
class MobArmorEquipmentPacket:
    """Every armor slot at once, where MobEquipmentPacket carries one at a time."""

    runtime_id: ActorRuntimeID
    head: SerializedNetworkItemStackDescriptor
    torso: SerializedNetworkItemStackDescriptor
    legs: SerializedNetworkItemStackDescriptor
    feet: SerializedNetworkItemStackDescriptor
    body: SerializedNetworkItemStackDescriptor
