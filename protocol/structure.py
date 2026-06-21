from enum import IntEnum

from protocol import field, int32, int64, packet, type, uint8, value, varint32, varint64
from protocol.common import BlockPos, NetworkBlockPos, Vec3
from protocol.nbt import CompoundTag

package = "bedrock.protocol"


@packet(id=314, since=712)
class CurrentStructureFeaturePacket:
    """Informs the client of which Structure Feature they are currently occupying."""

    current_structure_feature: str


@packet(id=313, since=712)
class JigsawStructureDataPacket:
    """Jigsaw Structure data used by client jigsaw structure worldgen. This packet contains a
    copy of the behavior pack jigsaw structure rules."""

    jigsaw_structure_data_tag: CompoundTag


class StructureBlockType(IntEnum):
    DATA = 0
    SAVE = 1
    LOAD = 2
    CORNER = 3
    INVALID = 4
    EXPORT = 5


class StructureRedstoneSaveMode(IntEnum):
    SAVES_TO_MEMORY = 0
    SAVES_TO_DISK = 1


class StructureRotation(IntEnum):
    NONE = 0
    ROTATE_90 = 1
    ROTATE_180 = 2
    ROTATE_270 = 3


class StructureMirror(IntEnum):
    NONE = 0
    X = 1
    Z = 2
    XZ = 3


class StructureAnimationMode(IntEnum):
    NONE = 0
    LAYERS = 1
    BLOCKS = 2


class StructureSettings:
    palette_name: str
    ignore_entities: bool
    ignore_blocks: bool
    allow_non_ticking_player_and_ticking_area_chunks: bool = field(since=503)
    structure_size: NetworkBlockPos = field(until=944)
    structure_size: BlockPos = field(since=944)
    structure_offset: NetworkBlockPos = field(until=944)
    structure_offset: BlockPos = field(since=944)
    last_touched_by_player: int64 = field(type=varint64)
    rotation: StructureRotation = field(type=uint8)
    mirror: StructureMirror = field(type=uint8)
    animation_mode: StructureAnimationMode = field(type=uint8, since=440)
    animation_seconds: float = field(since=440)
    integrity_value: float
    integrity_seed: int32
    pivot: Vec3 = field(since=388)


class StructureEditorData:
    structure_name: str
    filtered_structure_name: str = field(since=776)
    data_field: str
    include_players: bool
    show_bounding_box: bool
    structure_block_type: StructureBlockType = field(type=varint32)
    structure_settings: StructureSettings
    redstone_save_mode: StructureRedstoneSaveMode = field(type=varint32, since=388)


@packet(id=90)
class StructureBlockUpdatePacket:
    block_pos: NetworkBlockPos = field(until=944)
    block_pos: BlockPos = field(since=944)
    data: StructureEditorData
    trigger: bool
    is_waterlogged: bool = field(since=554)


@type(since=361)
class StructureTemplateRequestOperation(IntEnum):
    NONE = 0
    EXPORT_FROM_SAVE_MODE = 1
    EXPORT_FROM_LOAD_MODE = 2
    QUERY_SAVED_STRUCTURE = 3
    # TODO: gophertunnel removed this constant at v685 (1.21.20), CloudburstMC marks it
    # `@deprecated since v712`, and bedrock-headers (latest) omits it entirely. Until=685
    # reflects gophertunnel; confirm against an older BDS or older bedrock-headers snapshot.
    IMPORT_FROM_SAVE = value(4, since=560, until=685)


@packet(id=132, since=361)
class StructureTemplateDataRequestPacket:
    """Used to request structure information from a server. This is used to kick off the process
    of loading and returning a structure in a Tag from the server back to the client. Currently
    this functionality is completely disabled and does nothing."""

    structure_name: str
    structure_block_pos: NetworkBlockPos = field(until=944)
    structure_block_pos: BlockPos = field(since=944)
    structure_settings: StructureSettings
    request_operation: StructureTemplateRequestOperation = field(type=uint8)


@type(since=388)
class StructureTemplateResponseType(IntEnum):
    NONE = 0
    EXPORT = 1
    QUERY = 2


@packet(id=133, since=361)
class StructureTemplateDataResponsePacket:
    """This is used in exporting from load, exporting from save, and querying saved structures
    from structure blocks. The client sends a packet to the server, from there the structure is
    built and then put into a Tag where it is sent back to the client, from there you can view
    the structure in the Structure Block Screen. Currently this functionality is completely
    disabled and does nothing. Used to reply to a request for structure information."""

    structure_name: str
    has_structure_tag: bool
    structure_tag: CompoundTag = field(when=lambda p: p.has_structure_tag)
    response_type: StructureTemplateResponseType = field(type=uint8, since=388)
