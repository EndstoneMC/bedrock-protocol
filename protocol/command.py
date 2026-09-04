"""Commands: server/commands/ -- the command tree, origins, output, soft enums,
and both permission ladders."""

import uuid
from enum import Enum, IntEnum

from protocol import auto, field, int8, int32, int64, packet, uint8, uint16, uint32, uvarint32, value
from protocol.actor import ActorRuntimeID
from protocol.common import BlockPos
from protocol.network import NetworkBlockPosition

package = "bedrock.protocol"


class CommandPermissionLevel(IntEnum, uint8):
    ANY = 0
    GAME_DIRECTORS = 1
    ADMIN = 2
    HOST = 3
    OWNER = 4
    INTERNAL = 5


@packet(id=140)
class SettingsCommandPacket:
    command_string: str
    suppress_output: bool


@packet(id=76)
class AvailableCommandsPacket:
    class EnumData:
        name: str
        values: list[uint32]

    class ChainedSubcommandRelationship:
        sub_command_first_value: uvarint32
        sub_command_second_value: uvarint32

    class ChainedSubcommandData:
        name: str
        values: list[ChainedSubcommandRelationship]

    class SoftEnumData:
        name: str
        values: list[str]

    class ConstrainedValueData:
        enum_value_symbol: uint32
        enum_symbol: uint32
        constraints: list[uint8]

    class ParamData:
        name: str
        parse_symbol: uint32
        optional: bool
        param_options: uint8

    class OverloadData:
        is_chaining: bool
        params: list[ParamData]

    class CommandData:
        name: str
        description: str
        flags: uint16
        permission: CommandPermissionLevel = field(type=str)
        alias_enum: int32
        chained_subcommand_indexes: list[uint32]
        overloads: list[OverloadData]

    enum_values: list[str]
    chained_subcommand_values: list[str]
    postfixes: list[str]
    enums: list[EnumData]
    chained_subcommands: list[ChainedSubcommandData]
    commands: list[CommandData]
    soft_enums: list[SoftEnumData]
    constraints: list[ConstrainedValueData]


class CommandBlockMode(IntEnum, uint16):
    NORMAL = 0
    REPEATING = 1
    CHAIN = 2


@packet(id=78, until=944)
class CommandBlockUpdatePacket:
    class EntityCommandTarget:
        entity_id: ActorRuntimeID

    class BlockCommandData:
        block_pos: NetworkBlockPosition
        mode: CommandBlockMode
        redstone_mode: bool
        is_conditional: bool

    target: EntityCommandTarget | BlockCommandData
    command: str
    last_output: str
    name: str
    filtered_name: str
    track_output: bool
    tick_delay: uint32
    execute_on_first_tick: bool


@packet(id=78, since=944, until=2168)
class CommandBlockUpdatePacket:
    class EntityCommandTarget:
        entity_id: ActorRuntimeID

    class BlockCommandData:
        block_pos: BlockPos
        mode: CommandBlockMode
        redstone_mode: bool
        is_conditional: bool

    target: EntityCommandTarget | BlockCommandData
    command: str
    last_output: str
    name: str
    filtered_name: str
    track_output: bool
    tick_delay: uint32
    execute_on_first_tick: bool


@packet(id=78, since=2168)
class CommandBlockUpdatePacket:
    class EntityCommandTarget:
        entity_id: ActorRuntimeID

    class BlockCommandData:
        block_pos: BlockPos
        mode: CommandBlockMode
        redstone_mode: bool
        is_conditional: bool

    target: EntityCommandTarget | BlockCommandData
    command: str
    last_output: str
    name: str
    filtered_name: str
    track_output: bool
    tick_delay: int32
    execute_on_first_tick: bool


class CommandOriginType(Enum, uint8):
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


class CommandOriginData:
    type: CommandOriginType = field(type=str)
    uuid: uuid.UUID
    request_id: str
    player_id: int64


class CurrentCmdVersion(Enum):
    INVALID = -1
    INITIAL = 1
    TP_ROTATION_CLAMPING = 2
    NEW_BEDROCK_CMD_SYSTEM = 3
    EXECUTE_USES_VEC3 = 4
    CLONE_FIXES = 5
    UPDATE_AQUATIC = 6
    ENTITY_SELECTOR_USES_VEC3 = 7
    CONTAINERS_DONT_DROP_ITEMS_ANYMORE = 8
    FILTERS_OBEY_DIMENSIONS = 9
    EXECUTE_AND_BLOCK_COMMAND_AND_SELF_SELECTOR_FIXES = 10
    INSTANT_EFFECTS_USE_TICKS = 11
    DONT_REGISTER_BROKEN_FUNCTION_COMMANDS = 12
    CLEAR_SPAWN_POINT_COMMAND = 13
    CLONE_AND_TELEPORT_ROTATION_FIXES = 14
    TELEPORT_DIMENSION_FIXES = 15
    CLONE_UPDATE_BLOCK_AND_TIME_FIXES = 16
    CLONE_INTERSECT_FIX = 17
    FUNCTION_EXECUTE_ORDER_AND_CHEST_SLOT_FIX = 18
    NON_TICKING_AREAS_NO_LONGER_CONSIDERED_LOADED = 19
    SPREADPLAYERS_HAZARD_AND_RESOLVE_PLAYER_BY_NAME_FIX = 20
    NEW_EXECUTE_COMMAND_SYNTAX_EXPERIMENT_AND_CHEST_LOOT_TABLE_FIX_AND_TELEPORT_FACING_VERTICAL_UNCLAMPED_AND_LOCATE_BIOME_AND_FEATURE_MERGED = 21  # noqa: E501
    WATERLOGGING_ADDED_TO_STRUCTURE_COMMAND = 22
    SELECTOR_DISTANCE_FILTERED_AND_RELATIVE_ROTATION_FIX = 23
    NEW_SUMMON_COMMAND_ADDED_ROTATION_OPTIONS_AND_BUBBLE_COLUMN_CLONE_FIX_AND_EXECUTE_IN_DIMENSION_TELEPORT_FIX_AND_NEW_EXECUTE_ROTATION_FIX = 24  # noqa: E501
    NEW_EXECUTE_COMMAND_RELEASE_ENCHANT_COMMAND_LEVEL_FIX_AND_HAS_ITEM_DATA_FIX_AND_COMMAND_DEFERRAL = 25
    EXECUTE_IF_SCORE_FIXES = 26
    REPLACE_ITEM_AND_LOOT_REPLACE_BLOCK_COMMANDS_DO_NOT_PLACE_ITEMS_INTO_CAULDRONS_FIX = 27
    CHANGES_TO_COMMAND_ORIGIN_ROTATION = 28
    REMOVE_AUX_VALUE_PARAMETER_FROM_BLOCK_COMMANDS = 29
    VOLUME_SELECTOR_FIXES = 30
    ENABLE_SUMMON_ROTATION = 31
    SUMMON_COMMAND_DEFAULT_ROTATION = 32
    POSITIONAL_DIMENSION_FILTERING = 33
    COMMAND_SELECTOR_HAS_ITEM_FILTER_NO_LONGER_CALLS_SAME_ITEM_FUNCTION = 34
    AGENT_SWEEPING_BLOCK_TEST = 34
    BLOCK_STATE_EQUALS = 35
    COMMAND_POSITION_FIX = 35
    COMMAND_SELECTOR_HAS_ITEM_FILTER_USES_DATA_AS_DAMAGE_FOR_SELECTING_DAMAGEABLE_ITEMS = 36
    EXECUTE_DETECT_CONDITION_SUBCOMMAND_NOT_ALLOW_NON_LOADED_BLOCKS = 37
    REMOVE_SUICIDE_KEYWORD = 38
    CLONE_CONTAINER_BLOCK_ENTITY_REMOVAL_FIX = 39
    STOP_SOUND_MUSIC_FIX = 40
    SPREAD_PLAYERS_STUCK_IN_GROUND_FIX_AND_MAX_HEIGHT_PARAMETER = 41
    LOCATE_STRUCTURE_OUTPUT = 42
    POST_BLOCK_FLATTENING = 43
    TEST_FOR_BLOCK_COMMAND_DOES_NOT_IGNORE_BLOCK_STATE = 44
    CLONE_EXTRA_BLOCK_FILTER_FIX = 45
    FILL_COMMAND_UNFILLABLE_ERROR_OUTPUT = value(46, since=975)
    STOP_SOUND_OUTPUT_FIX = value(47, since=1001)
    PLAY_SOUND_OUTPUT_FIX = value(48, since=1001)
    PLAYER_WAYPOINTS_GAMERULE = value(49, since=1001)
    CLONE_PARTIAL_BED_BLOCK_FIX = value(50, since=2168)
    COUNT = auto()


@packet(id=77)
class CommandRequestPacket:
    command: str
    origin: CommandOriginData
    internal_source: bool
    version: CurrentCmdVersion = field(type=str)


class CommandOutputType(Enum):
    NONE = 0
    LAST_OUTPUT = 1
    SILENT = 2
    ALL_OUTPUT = 3
    DATA_SET = 4


class CommandOutputMessage:
    message_id: str
    successful: bool
    params: list[str]


class CommandOutput:
    type: CommandOutputType = field(type=str)
    success_count: uint32
    messages: list[CommandOutputMessage]
    data: str | None


@packet(id=79)
class CommandOutputPacket:
    origin_data: CommandOriginData
    output: CommandOutput


class SoftEnumUpdateType(IntEnum, uint8):
    ADD = 0
    REMOVE = 1
    REPLACE = 2


@packet(id=114)
class UpdateSoftEnumPacket:
    enum_name: str
    values: list[str]
    type: SoftEnumUpdateType


class PlayerPermissionLevel(IntEnum, int8):
    VISITOR = 0
    MEMBER = 1
    OPERATOR = 2
    CUSTOM = 3
