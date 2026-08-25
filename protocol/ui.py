from protocol import packet

package = "bedrock.protocol"


@packet(id=335, since=2168)
class ClientboundDataDrivenUIReloadPacket:
    pass
