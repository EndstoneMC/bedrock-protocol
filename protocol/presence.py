import uuid

from protocol import packet, type

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
    scenario_id: str | None
    server_id: str | None


class ClientStoreEntryPointConfiguration:
    store_id: str
    store_name: str


class ServerConfigurationJoinInfo:
    gatherings_configuration_join_info: GatheringsConfigurationJoinInfo | None
    client_store_entrypoint_configuration: ClientStoreEntryPointConfiguration | None
    presence_configuration: PresenceConfiguration | None


class ServerTelemetryData:
    server_id: str
    scenario_id: str
    world_id: str
    owner_id: str


@packet(id=347)
class ServerPresenceInfoPacket:
    presence_configuration: PresenceConfiguration | None
