from protocol import packet
from protocol.actor import ActorRuntimeID
from protocol.inventory import SerializedNetworkItemStackDescriptor

package = "bedrock.protocol"


@packet(id=32)
class MobArmorEquipmentPacket:
    """Every armor slot at once, where MobEquipmentPacket carries one at a time."""

    runtime_id: ActorRuntimeID
    head: SerializedNetworkItemStackDescriptor
    torso: SerializedNetworkItemStackDescriptor
    legs: SerializedNetworkItemStackDescriptor
    feet: SerializedNetworkItemStackDescriptor
    body: SerializedNetworkItemStackDescriptor
