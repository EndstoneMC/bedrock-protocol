from enum import Enum

from protocol import field, int8, packet

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


class PartyDestinationCookieIntent(Enum, int8):
    NOTIFY = 0
    OPT_IN = 1, "OptIn"
    OPT_OUT = 2, "OptOut"


@packet(id=349, since=2168)
class SendPartyDestinationCookiePacket:
    cookie: str
    intent: PartyDestinationCookieIntent = field(type=str)
    destination_name: str
