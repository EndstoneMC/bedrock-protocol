"""Structures and the harness that lays them out: world/level/levelgen/structure/
and gametest/ -- structure blocks, templates, jigsaws, features, ticking areas."""

from enum import IntEnum, auto

from protocol import field, packet, type, uint8, uint32, value, varint32
from protocol.actor import ActorUniqueID
from protocol.common import BlockPos, Vec3
from protocol.item_stack import RedactableString
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


type RandomSeed = uint32


class StructureBlockType(IntEnum):
    DATA = 0
    SAVE = 1
    LOAD = 2
    CORNER = 3
    INVALID = 4
    EXPORT = 5
    COUNT = auto()


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
    TOTAL = auto()


class Mirror(IntEnum, uint8):
    NONE = 0
    X = 1
    Z = 2
    XZ = value(3, cpp_name="XZ")


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


@packet(id=179)
class TickingAreasLoadStatusPacket:
    waiting_for_preload: bool


@packet(id=314)
class CurrentStructureFeaturePacket:
    current_structure_feature: str


class StructureTemplateRequestOperation(IntEnum, uint8):
    NONE = 0
    EXPORT_FROM_SAVE_MODE = 1
    EXPORT_FROM_LOAD_MODE = 2
    QUERY_SAVED_STRUCTURE = 3


@packet(id=132)
class StructureTemplateDataRequestPacket:
    structure_name: str
    structure_block_pos: BlockPos
    structure_settings: StructureSettings
    request_operation: StructureTemplateRequestOperation


class StructureTemplateResponseType(IntEnum, uint8):
    NONE = 0
    EXPORT = 1
    QUERY = 2


@packet(id=133)
class StructureTemplateDataResponsePacket:
    structure_name: str
    structure_tag: CompoundTag | None
    response_type: StructureTemplateResponseType


@packet(id=313)
class JigsawStructureDataPacket:
    jigsaw_structure_data_tag: CompoundTag


class FeatureRegistry:
    class FeatureBinaryJsonFormat:
        feature_name: str
        binary_json_output: str


@packet(id=191)
class FeatureRegistryPacket:
    features_data_list: list[FeatureRegistry.FeatureBinaryJsonFormat]


@packet(id=195)
class GameTestResultsPacket:
    succeeded: bool
    error: str
    test_name: str


@packet(id=194)
class GameTestRequestPacket:
    max_tests_per_batch: varint32
    repeat_count: varint32
    rotation: Rotation
    stop_on_failure: bool
    test_pos: BlockPos
    tests_per_row: varint32
    test_name: str
