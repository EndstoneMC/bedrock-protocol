from protocol import field, int32, packet, uint8
from protocol.actor import ActorRuntimeID
from protocol.inventory import ContainerID, SerializedNetworkItemStackDescriptor

package = "bedrock.protocol"


# TODO: the 975 form is known and equal to this one -- protocol-docs r26_u2 dumps the packet
# cerealised with the same fields -- but SerializedNetworkItemStackDescriptor resolves to the
# pre-cereal shape at 975, which packets 30/32/49 still needed there. Modelling 975 needs the
# pre-cereal descriptor under its own name.
@packet(id=31, since=1001)
class MobEquipmentPacket:
    """One slot at a time, where MobArmorEquipmentPacket carries every armor slot."""

    runtime_id: ActorRuntimeID
    item: SerializedNetworkItemStackDescriptor
    slot: int32 = field(type=uint8)
    selected_slot: int32 = field(type=uint8)
    container_id: ContainerID


@packet(id=32)
class MobArmorEquipmentPacket:
    """Every armor slot at once, where MobEquipmentPacket carries one at a time."""

    runtime_id: ActorRuntimeID
    head: SerializedNetworkItemStackDescriptor
    torso: SerializedNetworkItemStackDescriptor
    legs: SerializedNetworkItemStackDescriptor
    feet: SerializedNetworkItemStackDescriptor
    body: SerializedNetworkItemStackDescriptor
