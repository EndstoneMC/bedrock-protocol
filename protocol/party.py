from protocol import packet

package = "bedrock.protocol"


@packet(id=350, since=2168)
class PartyDestinationCookieResponsePacket:
    cookie: str
    accepted: bool
