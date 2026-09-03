"""The server's session presence: gathering configuration, store entry point,
telemetry identity, the player's party, and transfer."""

import uuid
from enum import Enum

from protocol import field, int8, packet, type, uint16

package = "bedrock.protocol"


@type(until=1001)
class PresenceConfiguration:
    experience_name: str
    world_name: str


@type(since=1001, until=2168)
class PresenceConfiguration:
    experience_name: str | None
    world_name: str | None
    rich_presence_id: str


@type(since=2168)
class PresenceConfiguration:
    rich_presence_id: str | None


@type(until=2168)
class GatheringsConfigurationJoinInfo:
    experience_id: uuid.UUID
    experience_name: str
    experience_world_id: uuid.UUID
    experience_world_name: str
    creator_id: str
    target_id: uuid.UUID
    scenario_id: str
    server_id: str


@type(since=2168)
class GatheringsConfigurationJoinInfo:
    experience_id: uuid.UUID
    experience_name: str
    experience_world_id: uuid.UUID | None
    experience_world_name: str | None
    creator_id: str
    target_id: uuid.UUID | None
    mpsas_scenario_id: str | None
    server_id: str | None


class ClientStoreEntryPointConfiguration:
    store_id: str
    store_name: str


class ServerConfigurationJoinInfo:
    gatherings_configuration: GatheringsConfigurationJoinInfo | None
    client_store_entry_point_configuration: ClientStoreEntryPointConfiguration | None
    presence_configuration: PresenceConfiguration | None


class ServerTelemetryData:
    server_id: str
    scenario_id: str
    world_id: str
    owner_id: str


@packet(id=347)
class ServerPresenceInfoPacket:
    presence_configuration: PresenceConfiguration | None


@packet(id=85)
class TransferPacket:
    destination: str
    destination_port: uint16
    reload_world: bool
    gatherings_configuration: GatheringsConfigurationJoinInfo | None = field(since=2168)


@packet(id=350, since=2168)
class PartyDestinationCookieResponsePacket:
    cookie: str
    accepted: bool


class PlayerPartyInfo:
    party_id: str
    is_leader: bool


@packet(id=342)
class PartyChangedPacket:
    party_info: PlayerPartyInfo | None


class PartyDestinationCookieIntent(Enum, int8):
    NOTIFY = 0
    OPT_IN = 1
    OPT_OUT = 2


@packet(id=349, since=2168)
class SendPartyDestinationCookiePacket:
    cookie: str
    intent: PartyDestinationCookieIntent = field(type=str)
    destination_name: str
