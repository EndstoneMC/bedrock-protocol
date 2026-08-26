from protocol import packet

package = "bedrock.protocol"


@packet(id=350, since=2168)
class PartyDestinationCookieResponsePacket:
    cookie: str
    accepted: bool


class PlayerPartyInfo:
    party_id: str
    is_leader: bool


@packet(id=342, since=2168)
class PartyChangedPacket:
    party_info: PlayerPartyInfo | None
