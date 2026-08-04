from enum import IntEnum

from protocol import field, int32, packet, type, uint8, varint64
from protocol.actor import ActorUniqueID

package = "bedrock.protocol"


class ScoreboardId:
    raw_id: varint64


class PlayerScoreboardId:
    actor_unique_id: varint64


class IdentityDefinition:
    class Type(IntEnum, uint8):
        INVALID = 0
        PLAYER = 1
        ENTITY = 2
        FAKE_PLAYER = 3


class ScorePacketType(IntEnum, uint8):
    CHANGE = 0
    REMOVE = 1


# TODO: confirm against BDS -- this reaches the wire name-coded, in the PEP 8
# spelling, so CHANGE_PLAYER lowercases to change_player where CloudburstMC v2168
# writes "changeplayer". Casing is not load-bearing but the inserted underscore is,
# and persona::PieceType shows BDS does use snake_case wire names elsewhere.
@type(since=2168)
class ScorePacketEntryAction(IntEnum, uint8):
    REMOVE = 0
    CHANGE_PLAYER = 1
    CHANGE_ENTITY = 2
    CHANGE_FAKE_PLAYER = 3


class ScoreboardIdentityPacketType(IntEnum, uint8):
    UPDATE = 0
    REMOVE = 1


class ScorePacketInfo:
    scoreboard_id: ScoreboardId
    objective_name: str
    score_value: int32
    identity_type: IdentityDefinition.Type
    player_id: PlayerScoreboardId = field(when=lambda i: i.identity_type == IdentityDefinition.Type.PLAYER)
    entity_id: ActorUniqueID = field(when=lambda i: i.identity_type == IdentityDefinition.Type.ENTITY)
    fake_player_name: str = field(when=lambda i: i.identity_type == IdentityDefinition.Type.FAKE_PLAYER)


@type(since=2168)
class RemoveScore:
    action: ScorePacketEntryAction = field(type=str)
    scoreboard_id: ScoreboardId
    objective_name: str | None


@type(since=2168)
class ChangePlayerScore:
    action: ScorePacketEntryAction = field(type=str)
    scoreboard_id: ScoreboardId
    objective_name: str
    score_value: int32
    player_unique_id: PlayerScoreboardId


@type(since=2168)
class ChangeEntityScore:
    action: ScorePacketEntryAction = field(type=str)
    scoreboard_id: ScoreboardId
    objective_name: str
    score_value: int32
    actor_id: ActorUniqueID


@type(since=2168)
class ChangeFakePlayerScore:
    action: ScorePacketEntryAction = field(type=str)
    scoreboard_id: ScoreboardId
    objective_name: str
    score_value: int32
    fake_player_name: str


@type(until=2168)
class ScoreboardIdentityPacketInfo:
    scoreboard_id: ScoreboardId
    player_id: PlayerScoreboardId


@type(since=2168)
class ScoreboardIdentityPacketInfo:
    scoreboard_id: ScoreboardId
    player_id: PlayerScoreboardId | None


@packet(id=108, until=2168)
class SetScorePacket:
    # TODO: field(when=) cannot reach the enclosing packet, so BDS's single
    # mScoreInfo is spelled as two whole-list gates on mType, and the remove-case
    # entry earns a name BDS does not have.
    class RemovedScorePacketInfo:
        scoreboard_id: ScoreboardId
        objective_name: str
        score_value: int32

    type: ScorePacketType
    score_info: list[ScorePacketInfo] = field(when=lambda p: p.type == ScorePacketType.CHANGE)
    removed_score_info: list[RemovedScorePacketInfo] = field(when=lambda p: p.type == ScorePacketType.REMOVE)


@packet(id=108, since=2168)
class SetScorePacket:
    score_info: list[RemoveScore | ChangePlayerScore | ChangeEntityScore | ChangeFakePlayerScore]


@packet(id=112, until=2168)
class SetScoreboardIdentityPacket:
    # TODO: field(when=) cannot reach the enclosing packet, so BDS's single
    # mIdentityInfo is spelled as two whole-list gates on mType.
    type: ScoreboardIdentityPacketType
    identity_info: list[ScoreboardIdentityPacketInfo] = field(
        when=lambda p: p.type == ScoreboardIdentityPacketType.UPDATE
    )
    removed_identity_info: list[ScoreboardId] = field(
        when=lambda p: p.type == ScoreboardIdentityPacketType.REMOVE
    )


@packet(id=112, since=2168)
class SetScoreboardIdentityPacket:
    type: ScoreboardIdentityPacketType
    identity_info: list[ScoreboardIdentityPacketInfo]
