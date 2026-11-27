"""Packets and types relating to starting a game and changing its settings."""

import uuid
from enum import IntEnum

from protocol import field, int16, int32, packet, type, uint8, uint16, uint64, uvarint32, varint32
from protocol.actor import ActorRuntimeID, ActorUniqueID, PlayerInputTick
from protocol.block import BlockEntry, ServerBlockProperty
from protocol.common import Vec2, Vec3
from protocol.level import Difficulty, GameRulesChangedPacketData, GameType, LevelSettings
from protocol.nbt import CompoundTag
from protocol.network import NetworkPermissions
from protocol.player import SyncedPlayerMovementSettings
from protocol.presence import ServerConfigurationJoinInfo
from protocol.telemetry import ServerTelemetryData

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"
go_package = "github.com/EndstoneMC/bedrock-protocol/go/protocol"


@packet(id=11, until=2168)
class StartGamePacket:
    entity_id: ActorUniqueID
    runtime_id: ActorRuntimeID
    entity_game_type: GameType
    pos: Vec3
    rot: Vec2
    settings: LevelSettings
    level_id: str
    level_name: str
    template_content_identity: str
    is_trial: bool
    movement_settings: SyncedPlayerMovementSettings
    level_current_time: uint64
    enchantment_seed: varint32
    block_properties: list[BlockEntry]
    items: list[StartGameItemEntry] = field(until=776)
    multiplayer_correlation_id: str
    enable_item_stack_net_manager: bool
    server_version: str
    player_property_data: CompoundTag
    server_block_type_registry_checksum: uint64
    world_template_id: uuid.UUID
    server_enabled_client_side_generation: bool
    block_network_ids_are_hashes: bool
    tick_death_systems_enabled: bool = field(since=827, until=898)
    network_permissions: NetworkPermissions
    is_logging_chat: bool = field(since=1001)
    with field(since=924):
        server_configuration_join_info: ServerConfigurationJoinInfo | None
        server_telemetry_data: ServerTelemetryData


@packet(id=11, since=2168)
class StartGamePacket:
    entity_id: ActorUniqueID
    runtime_id: ActorRuntimeID
    entity_game_type: GameType
    pos: Vec3
    rot: Vec2
    settings: LevelSettings
    level_id: str
    level_name: str
    template_content_identity: str
    is_trial: bool
    movement_settings: SyncedPlayerMovementSettings
    level_current_time: uint64
    enchantment_seed: varint32
    block_properties: list[ServerBlockProperty]
    multiplayer_correlation_id: str
    enable_item_stack_net_manager: bool
    server_version: str
    player_property_data: CompoundTag
    server_block_type_registry_checksum: uint64
    world_template_id: uuid.UUID
    server_enabled_client_side_generation: bool
    block_network_ids_are_hashes: bool
    network_permissions: NetworkPermissions
    server_configuration_join_info: ServerConfigurationJoinInfo | None
    server_telemetry_data: ServerTelemetryData


@packet(id=72)
class GameRulesChangedPacket:
    rule_data: GameRulesChangedPacketData


@packet(id=59)
class SetCommandsEnabledPacket:
    commands_enabled: bool


@packet(id=60)
class SetDifficultyPacket:
    difficulty: Difficulty = field(type=uvarint32)


@packet(id=62)
class SetPlayerGameTypePacket:
    player_game_type: GameType


@packet(id=75)
class ShowCreditsPacket:
    class CreditsState(IntEnum, int32):
        START = 0
        FINISHED = 1

    player_id: ActorRuntimeID
    credits_state: CreditsState


@packet(id=105)
class SetDefaultGameTypePacket:
    default_game_type: GameType


class MultiplayerSettingsPacketType(IntEnum, int32):
    ENABLE_MULTIPLAYER = 0
    DISABLE_MULTIPLAYER = 1
    REFRESH_JOINCODE = 2


@packet(id=139)
class MultiplayerSettingsPacket:
    packet_type: MultiplayerSettingsPacketType


@packet(id=151)
class UpdatePlayerGameTypePacket:
    player_game_type: GameType
    target_player: ActorUniqueID
    tick: PlayerInputTick = field(type=uvarint32, since=671, until=748)
    tick: PlayerInputTick = field(since=748)


class SimulationType(IntEnum, uint8):
    GAME = 0
    EDITOR = 1
    TEST = 2
    INVALID = 3


@packet(id=168)
class SimulationTypePacket:
    sim_type: SimulationType


@packet(id=64)
class SimpleEventPacket:
    class Subtype(IntEnum, uint16):
        UNINITIALIZED_SUBTYPE = 0
        ENABLE_COMMANDS = 1
        DISABLE_COMMANDS = 2
        UNLOCK_WORLD_TEMPLATE_SETTINGS = 3

    subtype: Subtype = field(type=uint16)


@type(until=776)
class StartGameItemEntry:
    name: str
    id: int16
    is_component_based: bool
