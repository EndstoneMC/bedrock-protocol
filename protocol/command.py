from enum import IntEnum

from protocol import field, int32, packet, uint8, uint16, uint32, uvarint32, value
from protocol.actor import ActorRuntimeID
from protocol.common import BlockPos

package = "bedrock.protocol"


class CommandPermissionLevel(IntEnum, uint8):
    ANY = 0
    GAME_DIRECTORS = value(1, "GameDirectors")
    ADMIN = 2
    HOST = 3
    OWNER = 4
    INTERNAL = 5


@packet(id=140, since=2168)
class SettingsCommandPacket:
    command_string: str
    suppress_output: bool


@packet(id=76, since=2168)
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
