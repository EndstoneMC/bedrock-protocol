"""Scoreboard ids, identities, objectives and scores: world/scores/."""

from enum import IntEnum
from typing import Literal

from protocol import field, int32, packet, type, uint8, varint32, varint64
from protocol.actor import ActorUniqueID

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"


class ScoreboardId:
    raw_id: varint64


class PlayerScoreboardId:
    actor_unique_id: ActorUniqueID


class IdentityDefinition:
    class Type(IntEnum, uint8):
        INVALID = 0
        PLAYER = 1
        ENTITY = 2
        FAKE_PLAYER = 3


@type(since=2168)
class ScorePacketEntryAction(IntEnum, uint8):
    REMOVE = 0
    CHANGE_PLAYER = 1
    CHANGE_ENTITY = 2
    CHANGE_FAKE_PLAYER = 3


class ScoreboardIdentityPacketType(IntEnum, uint8):
    UPDATE = 0
    REMOVE = 1


@type(since=2168)
class RemoveScore:
    action: Literal["remove"]
    scoreboard_id: ScoreboardId
    objective_name: str | None


@type(since=2168)
class ChangePlayerScore:
    action: Literal["changeplayer"]
    scoreboard_id: ScoreboardId
    objective_name: str
    score_value: int32
    player_id: PlayerScoreboardId


@type(since=2168)
class ChangeEntityScore:
    action: Literal["changeentity"]
    scoreboard_id: ScoreboardId
    objective_name: str
    score_value: int32
    entity_id: ActorUniqueID


@type(since=2168)
class ChangeFakePlayerScore:
    action: Literal["changefakeplayer"]
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
    player_id: ActorUniqueID | None


@packet(id=108, until=2168)
class SetScorePacket:
    # TODO: one mScoreInfo, without RemovedScorePacketInfo, once field(when=) can read the enclosing packet
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
    # TODO: one mIdentityInfo once field(when=) can read the enclosing packet
    type: ScoreboardIdentityPacketType
    identity_info: list[ScoreboardIdentityPacketInfo] = field(
        when=lambda p: p.type == ScoreboardIdentityPacketType.UPDATE
    )
    removed_identity_info: list[ScoreboardId] = field(when=lambda p: p.type == ScoreboardIdentityPacketType.REMOVE)


@packet(id=112, since=2168)
class SetScoreboardIdentityPacket:
    type: ScoreboardIdentityPacketType
    identity_info: list[ScoreboardIdentityPacketInfo]


@packet(id=106)
class RemoveObjectivePacket:
    objective_name: str


class ObjectiveSortOrder(IntEnum, uint8):
    ASCENDING = 0
    DESCENDING = 1


@packet(id=107)
class SetDisplayObjectivePacket:
    display_slot_name: str
    objective_name: str
    objective_display_name: str
    criteria_name: str
    sort_order: ObjectiveSortOrder = field(type=varint32)


@type(until=2168)
class ScorePacketType(IntEnum, uint8):
    CHANGE = 0
    REMOVE = 1


@type(until=2168)
class ScorePacketInfo:
    scoreboard_id: ScoreboardId
    objective_name: str
    score_value: int32
    identity_type: IdentityDefinition.Type
    player_id: PlayerScoreboardId = field(when=lambda i: i.identity_type == IdentityDefinition.Type.PLAYER)
    entity_id: ActorUniqueID = field(when=lambda i: i.identity_type == IdentityDefinition.Type.ENTITY)
    fake_player_name: str = field(when=lambda i: i.identity_type == IdentityDefinition.Type.FAKE_PLAYER)
