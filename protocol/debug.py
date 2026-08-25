from protocol import packet

package = "bedrock.protocol"


@packet(id=190, since=2168)
class EditorNetworkPacket:
    route_to_manager: bool
    raw_variant_name: str
    raw_variant_data: str
