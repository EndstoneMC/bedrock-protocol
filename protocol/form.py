from protocol import packet, uvarint32

package = "bedrock.protocol"


@packet(id=100, since=2168)
class ModalFormRequestPacket:
    form_id: uvarint32
    form_json: str
