from enum import IntEnum, auto

from protocol import field, int8, int32, packet, type, uint8, uint32, uvarint32, value, varint32
from protocol.actor import ActorUniqueID
from protocol.common import BlockPos, Color

package = "bedrock.protocol"


@type(until=2168)
class MapItemTrackedActor:
    class Type(IntEnum):
        ENTITY = 0
        BLOCK_ENTITY = 1
        OTHER = 2

    @type(until=2168)
    class UniqueId:
        type: "MapItemTrackedActor.Type" = field(type=int32)
        key_entity_id: ActorUniqueID = field(when=lambda u: u.type == MapItemTrackedActor.Type.ENTITY)
        key_block_pos: BlockPos = field(when=lambda u: u.type == MapItemTrackedActor.Type.BLOCK_ENTITY)


@type(since=2168)
class MapItemTrackedActor:
    class Type(IntEnum):
        ENTITY = 0
        BLOCK_ENTITY = 1
        OTHER = 2

    @type(since=2168)
    class UniqueId:
        type: "MapItemTrackedActor.Type" = field(type=int32)
        key_entity_id: ActorUniqueID | None
        key_block_pos: BlockPos | None


@type(until=2168)
class MapDecoration:
    class Type(IntEnum, int8):
        MARKER_WHITE = 0
        MARKER_GREEN = 1
        MARKER_RED = 2
        MARKER_BLUE = 3
        X_WHITE = 4
        TRIANGLE_RED = 5
        SQUARE_WHITE = 6
        MARKER_SIGN = 7
        MARKER_PINK = 8
        MARKER_ORANGE = 9
        MARKER_YELLOW = 10
        MARKER_TEAL = 11
        TRIANGLE_GREEN = 12
        SMALL_SQUARE_WHITE = 13
        MANSION = 14
        MONUMENT = 15
        NO_DRAW = 16
        VILLAGE_DESERT = 17
        VILLAGE_PLAINS = 18
        VILLAGE_SAVANNA = 19
        VILLAGE_SNOWY = 20
        VILLAGE_TAIGA = 21
        JUNGLE_TEMPLE = 22
        WITCH_HUT = 23
        TRIAL_CHAMBERS = 24
        COUNT = auto()

    image: Type
    rotation: int8
    x: int8
    y: int8
    label: str
    color: Color = field(type=uvarint32)


@type(since=2168)
class MapDecoration:
    class Type(IntEnum, int8):
        MARKER_WHITE = 0
        MARKER_GREEN = 1
        MARKER_RED = 2
        MARKER_BLUE = 3
        X_WHITE = 4
        TRIANGLE_RED = 5
        SQUARE_WHITE = 6
        MARKER_SIGN = 7
        MARKER_PINK = 8
        MARKER_ORANGE = 9
        MARKER_YELLOW = 10
        MARKER_TEAL = 11
        TRIANGLE_GREEN = 12
        SMALL_SQUARE_WHITE = 13
        MANSION = 14
        MONUMENT = 15
        NO_DRAW = 16
        VILLAGE_DESERT = 17
        VILLAGE_PLAINS = 18
        VILLAGE_SAVANNA = 19
        VILLAGE_SNOWY = 20
        VILLAGE_TAIGA = 21
        JUNGLE_TEMPLE = 22
        WITCH_HUT = 23
        TRIAL_CHAMBERS = 24
        ABANDONED_CAMP = value(25, since=2181)
        BURIED_ANCIENT_CITY = value(26, since=2181)
        BURIED_MINESHAFT = value(27, since=2181)
        DESERT_PYRAMID = value(28, since=2181)
        WARM_OCEAN_RUINS = value(29, since=2181)
        COUNT = auto()

    image: Type
    rotation: int8
    x: int8
    y: int8
    label: str
    color: Color


@packet(id=67, until=2168)
class ClientboundMapItemDataPacket:
    class Type(IntEnum):
        INVALID = 0
        TEXTURE_UPDATE = 2
        DECORATION_UPDATE = 4
        CREATION = 8

    map_id: ActorUniqueID
    type: uvarint32
    dimension: uint8
    locked: bool
    map_origin: BlockPos
    map_ids: list[ActorUniqueID] = field(when=lambda p: p.type & 8 != 0)
    scale: int8 = field(when=lambda p: p.type & 14 != 0)
    with field(when=lambda p: p.type & 4 != 0):
        unique_ids: list[MapItemTrackedActor.UniqueId]
        decorations: list[MapDecoration]
    with field(when=lambda p: p.type & 2 != 0):
        width: varint32
        height: varint32
        start_x: varint32
        start_y: varint32
        map_pixels: list[uvarint32]


@packet(id=67, since=2168)
class ClientboundMapItemDataPacket:
    class Type(IntEnum):
        INVALID = 0
        TEXTURE_UPDATE = 2
        DECORATION_UPDATE = 4
        CREATION = 8

    map_id: ActorUniqueID
    dimension: uint8
    locked: bool
    map_origin: BlockPos
    creation_map_ids: list[ActorUniqueID] | None
    scale: int8 | None
    unique_ids: list[MapItemTrackedActor.UniqueId] | None
    decorations: list[MapDecoration] | None
    width: varint32 | None
    height: varint32 | None
    start_x: varint32 | None
    start_y: varint32 | None
    map_pixels: list[uint32] | None
