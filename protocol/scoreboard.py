from enum import IntEnum

from protocol import field, int32, packet, uint8, varint32, varint64
from protocol.actor import ActorUniqueID

package = "bedrock.protocol"


@packet(id=106)
class RemoveObjectivePacket:
    """Using the scoreboard command, users can remove objectives that are tracked on the scoreboard."""

    objective_name: str


class ObjectiveSortOrder(IntEnum):
    ASCENDING = 0
    DESCENDING = 1


@packet(id=107)
class SetDisplayObjectivePacket:
    """Sent from the server for 3rd party content to display current objectives and status."""

    display_slot_name: str
    objective_name: str
    objective_display_name: str
    criteria_name: str
    sort_order: ObjectiveSortOrder = field(type=varint32)


class ScoreboardId:
    raw_id: varint64


class ScorePacketType(IntEnum):
    CHANGE = 0
    REMOVE = 1


class IdentityDefinitionType(IntEnum):
    INVALID = 0
    PLAYER = 1
    ENTITY = 2
    FAKE_PLAYER = 3


class ScoreRemoveEntry:
    scoreboard_id: ScoreboardId
    objective_name: str
    score_value: int32


class ScorePacketInfo:
    scoreboard_id: ScoreboardId
    objective_name: str
    score_value: int32
    identity_type: IdentityDefinitionType = field(type=uint8)
    entity_id: varint64 = field(
        when=lambda p: (
            p.identity_type == IdentityDefinitionType.PLAYER
            or p.identity_type == IdentityDefinitionType.ENTITY
        ),
    )
    fake_player_name: str = field(
        when=lambda p: p.identity_type == IdentityDefinitionType.FAKE_PLAYER,
    )


# Each entry's body is action-gated -- a CHANGE entry carries the full identity
# suffix (player / entity / fake-player name), a REMOVE entry stops after the
# leading (scoreboard_id, objective_name, score_value) triple. The DSL has no
# spelling for "every list element references the outer packet's discriminator"
# so the packet body below splits the wire form into two action-gated lists,
# each of which carries its own element type. Exactly one of the two is
# populated on a real packet.
@packet(id=108)
class SetScorePacket:
    type: ScorePacketType = field(type=uint8)
    change_entries: list[ScorePacketInfo] = field(
        when=lambda p: p.type == ScorePacketType.CHANGE,
    )
    remove_entries: list[ScoreRemoveEntry] = field(
        when=lambda p: p.type == ScorePacketType.REMOVE,
    )


class ScoreboardIdentityPacketType(IntEnum):
    UPDATE = 0
    REMOVE = 1


# CloudburstMC v291 wrote the per-entry identity as a UUID; gophertunnel and BDS
# write the player_id as a varint64 (the ActorUniqueID type), present only when
# the outer SetScoreboardIdentityPacket.type == UPDATE. The DSL has no spelling
# for "every list element references the outer packet's type discriminator", so
# the packet body below splits the wire form into two action-gated lists, each
# of which carries its own element type. Exactly one of the two is populated on
# a real packet.
class ScoreboardIdentityUpdateEntry:
    scoreboard_id: ScoreboardId
    player_id: ActorUniqueID


class ScoreboardIdentityRemoveEntry:
    scoreboard_id: ScoreboardId


@packet(id=112)
class SetScoreboardIdentityPacket:
    type: ScoreboardIdentityPacketType = field(type=uint8)
    update_entries: list[ScoreboardIdentityUpdateEntry] = field(
        when=lambda p: p.type == ScoreboardIdentityPacketType.UPDATE,
    )
    remove_entries: list[ScoreboardIdentityRemoveEntry] = field(
        when=lambda p: p.type == ScoreboardIdentityPacketType.REMOVE,
    )
