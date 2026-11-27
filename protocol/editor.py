"""Packets and types relating to Editor mode."""

from enum import IntEnum

from protocol import field, int8, int32, packet, type, uint8, value
from protocol.nbt import CompoundTag

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"
go_package = "github.com/EndstoneMC/bedrock-protocol/go/protocol"


@packet(id=190, until=944)
class EditorNetworkPacket:
    route_to_manager: bool = field(since=712)
    payload: CompoundTag


@packet(id=190, since=944)
class EditorNetworkPacket:
    route_to_manager: bool
    raw_variant_name: str
    raw_variant_data: str


class WorldType(IntEnum, int32):
    NON_EDITOR = 0
    EDITOR_PROJECT = 1
    EDITOR_TEST_LEVEL = 2
    EDITOR_REALMS_UPLOAD = value(3, since=800)


class EditorLevelMigrationVersion(IntEnum, int8):
    LEGACY = 0
    EDITOR_ACHIEVEMENTS = 1
    CURRENT = EDITOR_ACHIEVEMENTS


class ServerEditorConnectionPolicy(IntEnum, int32):
    MATCH_WORLD_TYPE = 0
    EDITOR_ONLY = 1
    VANILLA_ONLY = 2
    MIXED = 3


@type(since=2259)
class EditorPackType(IntEnum, uint8):
    NONE = 0
    CORE = 1
    ANNOTATION = 2
