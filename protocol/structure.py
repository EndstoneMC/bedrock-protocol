from enum import IntEnum

from protocol import field, packet, type, uint8, uint32, varint32
from protocol.actor import ActorUniqueID
from protocol.common import BlockPos, Vec3
from protocol.item_stack import RedactableString

package = "bedrock.protocol"


type RandomSeed = uint32


class StructureBlockType(IntEnum):
    DATA = 0
    SAVE = 1
    LOAD = 2
    CORNER = 3
    INVALID = 4
    EXPORT = 5


class StructureRedstoneSaveMode(IntEnum, uint8):
    SAVES_TO_MEMORY = 0
    SAVES_TO_DISK = 1


class Rotation(IntEnum, uint8):
    NONE = 0
    ROTATE_90 = 1
    ROTATE_180 = 2
    ROTATE_270 = 3
    CLOCKWISE_90 = 1
    CLOCKWISE_180 = 2
    COUNTER_CLOCKWISE_90 = 3


class Mirror(IntEnum, uint8):
    NONE = 0
    X = 1
    Z = 2
    XZ = 3


class AnimationMode(IntEnum, uint8):
    NONE = 0
    LAYERS = 1
    BLOCKS = 2


class StructureSettings:
    palette_name: str
    ignore_entities: bool
    ignore_blocks: bool
    allow_non_ticking_player_and_ticking_area_chunks: bool
    structure_size: BlockPos
    structure_offset: BlockPos
    last_touched_by_player: ActorUniqueID
    rotation: Rotation
    mirror: Mirror
    animation_mode: AnimationMode
    animation_seconds: float
    integrity_value: float
    integrity_seed: RandomSeed
    pivot: Vec3


@type(until=2168)
class StructureEditorData:
    structure_name: RedactableString
    data_field: str
    include_players: bool
    show_bounding_box: bool
    type: StructureBlockType
    settings: StructureSettings
    redstone_save_mode: StructureRedstoneSaveMode = field(type=varint32)


@type(since=2168)
class StructureEditorData:
    structure_name: RedactableString
    data_field: str
    include_players: bool
    show_bounding_box: bool
    type: StructureBlockType
    settings: StructureSettings
    redstone_save_mode: StructureRedstoneSaveMode


@packet(id=90)
class StructureBlockUpdatePacket:
    block_pos: BlockPos
    data: StructureEditorData
    trigger: bool
    is_waterlogged: bool
