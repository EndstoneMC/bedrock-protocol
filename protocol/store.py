from protocol import packet

package = "bedrock.protocol"


@packet(id=104, since=2168)
class ShowProfilePacket:
    player_xuid: str
