from protocol import packet

package = "bedrock.protocol"


@packet(id=177, since=2168)
class ScriptMessagePacket:
    message_id: str
    message_value: str
