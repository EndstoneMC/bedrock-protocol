from protocol import packet, type

package = "bedrock.protocol"


# BDS wraps this in `namespace ServerConfiguration`, which does not fold into the
# name.
@type(until=1001)
class PresenceConfiguration:
    experience_name: str
    world_name: str


# 999 turned both names optional and 980 appended rich_presence_id; both land on
# the same snapshot.
@type(since=1001)
class PresenceConfiguration:
    experience_name: str | None
    world_name: str | None
    rich_presence_id: str


@packet(id=347)
class ServerPresenceInfoPacket:
    presence_configuration: PresenceConfiguration | None
