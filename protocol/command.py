import uuid
from enum import IntEnum

from protocol import (
    field,
    int32,
    int64,
    packet,
    uint8,
    uint16,
    uint32,
    uvarint32,
    varint32,
    varint64,
)
from protocol.actor import ActorRuntimeID, CommandPermissionLevel
from protocol.common import BlockPos, NetworkBlockPos

package = "bedrock.protocol"


class CommandEnumConstraint(IntEnum):
    CHEATS_ENABLED = 0
    OPERATOR_PERMISSIONS = 1
    HOST_PERMISSIONS = 2


# bedrock-headers android/r21_u4 server/commands/CommandFlag.h models flags as
# eight per-axis enums (CommandUsageFlag/CommandVisibilityFlag/CommandSyncFlag/
# CommandExecuteFlag/CommandTypeFlag/CommandCheatFlag/CommandAsyncFlag/
# CommandEditorFlag) packed into struct CommandFlag::flag (uint16_t). The flat
# bitset below is the wire-side union of the non-zero values from those enums.
class CommandFlag(IntEnum):
    TEST = 1
    HIDDEN_FROM_COMMAND_BLOCK_ORIGIN = 2
    HIDDEN_FROM_PLAYER_ORIGIN = 4
    HIDDEN_FROM_AUTOMATION_ORIGIN = 8
    LOCAL = 16
    DISALLOWED = 32
    MESSAGE = 64
    NOT_CHEAT = 128
    ASYNC = 256
    NOT_EDITOR = 512


# Pre-v898 wrote the two indexes as uint16; v898 widened both to uint32. The
# v975 wire form (uint32) is modelled here; older shapes are noted in the
# field-level version gates of CommandData below.
class CommandChainedSubcommandRelationship:
    sub_command_first_value: uint32
    sub_command_second_value: uint32


class CommandChainedSubcommandData:
    name: str
    values: list[CommandChainedSubcommandRelationship]


class CommandSoftEnumData:
    name: str
    values: list[str]


class CommandConstrainedValueData:
    enum_value_symbol: int32
    enum_symbol: int32
    constraints: list[uint8]


# The `parse_symbol` packs both the parameter kind and an optional index into
# one of the packet's tables; the high bits choose between a primitive parser
# type, an enum (hard or soft), or a postfix string (CloudburstMC's
# writeParameter for the ARG_FLAG_VALID / ARG_FLAG_ENUM / ARG_FLAG_POSTFIX /
# ARG_FLAG_SOFT_ENUM bits 0x100000 / 0x200000 / 0x1000000 / 0x4000000).
class CommandParamData:
    name: str
    parse_symbol: uint32
    optional: bool
    # `param_options` is a bitmask over the CommandParamOption enum (CollapseEnum,
    # HasSemanticConstraint, EnumAutocompleteExpanded, etc.) -- one byte added in v340.
    param_options: uint8 = field(since=340)


# Pre-v594 carried no `is_chaining` flag.
class CommandOverloadData:
    is_chaining: bool = field(since=594)
    params: list[CommandParamData]


# Pre-v594 carried no chained subcommands; v594 added the
# `chained_subcommand_indexes` table and v898 widened those indexes from
# uint16 to uint32.
class CommandData:
    name: str
    description: str
    flags: uint8 = field(until=448)
    flags: uint16 = field(since=448)
    permission: CommandPermissionLevel = field(type=uint8, until=898)
    # v898 changed the wire form to the serialize-name string of the enum, but
    # the codegen doesn't apply field(type=str) overrides to cross-module enums
    # today. Model as a raw string for v898+; the higher layer maps the
    # serialize-name back to the enum.
    permission: str = field(since=898)
    alias_enum: int32
    chained_subcommand_indexes: list[uint16] = field(since=594, until=898)
    chained_subcommand_indexes: list[uint32] = field(since=898)
    overloads: list[CommandOverloadData]


# v898 widens the value-index elements to uint32 unconditionally.
class CommandEnumData:
    name: str
    # COMPILER_EXTENSION_NEEDED (until=898): each entry is one element from
    # the packet's `enum_values` string table, but the per-element width is
    # set per-packet, not per-element. CloudburstMC picks u8/u16/u32 based on
    # the total enum-values count. The DSL has no per-packet "list width" knob;
    # `field(prefix=...)` sets the count prefix, not the element size. The
    # `values` field is modelled below as the v898+ form.
    values: list[uint32]


@packet(id=76)
class AvailableCommandsPacket:
    """Contains all the available commands."""

    enum_values: list[str]
    chained_subcommand_values: list[str] = field(since=594)
    postfixes: list[str]
    enums: list[CommandEnumData]
    chained_subcommands: list[CommandChainedSubcommandData] = field(since=594)
    commands: list[CommandData]
    soft_enums: list[CommandSoftEnumData]
    constraints: list[CommandConstrainedValueData] = field(since=388)


class CommandBlockMode(IntEnum):
    NORMAL = 0
    REPEATING = 1
    CHAIN = 2


@packet(id=78)
class CommandBlockUpdatePacket:
    """Sent when you close the command block screen on the client."""

    is_block: bool
    block_pos: NetworkBlockPos = field(when=lambda p: p.is_block, until=944)
    block_pos: BlockPos = field(when=lambda p: p.is_block, since=944)
    mode: CommandBlockMode = field(type=uvarint32, when=lambda p: p.is_block)
    redstone_mode: bool = field(when=lambda p: p.is_block)
    is_conditional: bool = field(when=lambda p: p.is_block)
    entity_id: ActorRuntimeID = field(when=lambda p: not p.is_block)
    command: str
    last_output: str
    name: str
    filtered_name: str = field(since=776)
    track_output: bool
    tick_delay: int32 = field(since=361)
    execute_on_first_tick: bool = field(since=361)


class CommandOriginType(IntEnum):
    PLAYER = 0
    COMMAND_BLOCK = 1
    MINECART_COMMAND_BLOCK = 2
    DEV_CONSOLE = 3
    TEST = 4
    AUTOMATION_PLAYER = 5
    CLIENT_AUTOMATION = 6
    DEDICATED_SERVER = 7
    ENTITY = 8
    VIRTUAL = 9
    GAME_ARGUMENT = 10
    ENTITY_SERVER = 11
    PRECOMPILED = 12
    GAME_DIRECTOR_ENTITY_SERVER = 13
    SCRIPTING = 14
    EXECUTE_CONTEXT = 15


# Name from bedrock-headers (struct CommandOriginData in server/commands/CommandOriginData.h).
class CommandOriginData:
    type: CommandOriginType = field(type=uvarint32, until=898)
    type: CommandOriginType = field(type=str, since=898)
    uuid: uuid.UUID
    request_id: str
    # Pre-v898 the player_id was a varint64 written only when the origin type was
    # DEV_CONSOLE or TEST; v898 widened it to a bare little-endian int64 always.
    player_id: varint64 = field(
        when=lambda p: p.type == CommandOriginType.DEV_CONSOLE or p.type == CommandOriginType.TEST,
        until=898,
    )
    player_id: int64 = field(since=898)


class CommandOutputType(IntEnum):
    NONE = 0
    LAST_OUTPUT = 1
    SILENT = 2
    ALL_OUTPUT = 3
    DATA_SET = 4


class CommandOutputMessageType(IntEnum):
    SUCCESS = 0
    ERROR = 1


class CommandOutputMessage:
    # COMPILER_EXTENSION_NEEDED: v898 reordered this struct from
    # (success: bool, message_id: str, params: list[str]) to (message_id: str,
    # success: bool, params: list[str]); the DSL has no way to gate a per-field
    # reorder. The v975 shape (since=898) is modelled below.
    success: bool
    message_id: str
    params: list[str]


@packet(id=79)
class CommandOutputPacket:
    """\"slash\" command execution output, server to client."""

    origin_data: CommandOriginData
    output_type: CommandOutputType = field(type=uint8, until=898)
    output_type: CommandOutputType = field(type=str, since=898)
    success_count: uvarint32 = field(until=898)
    success_count: uint32 = field(since=898)
    messages: list[CommandOutputMessage]
    # Until v898 the trailing `data` was a bare string written only when
    # `output_type == DATA_SET`; since v898 it is an optional<string> emitted
    # unconditionally.
    data: str | None = field(since=898)


@packet(id=77)
class CommandRequestPacket:
    """'slash' command execution, client to server."""

    command: str
    origin: CommandOriginData
    internal_source: bool
    version: varint32 = field(since=567, until=898)
    version: str = field(since=898)


@packet(id=59)
class SetCommandsEnabledPacket:
    """This is used by the world settings screen, cheats, EDU builds for teachers,
    and various other places to enable cheats/commands."""

    commands_enabled: bool


@packet(id=140, since=388)
class SettingsCommandPacket:
    """Used when the player changes the world settings like doDayNightCycle or
    WeatherCycle via the world settings menu."""

    command_string: str
    suppress_output: bool


class SoftEnumUpdateType(IntEnum):
    ADD = 0
    REMOVE = 1
    REPLACE = 2


@packet(id=114)
class UpdateSoftEnumPacket:
    """This is used for the scoreboard and tag systems (overwhelmingly used by 3rd party
    content). This allows someone to sync between server and client tags and enums on
    mobs or on the level."""

    enum_name: str
    values: list[str]
    type: SoftEnumUpdateType = field(type=uint8)
