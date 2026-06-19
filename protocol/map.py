from enum import IntEnum, IntFlag

from protocol import field, int8, int32, packet, uint8, uint16, uint32, uvarint32, varint32
from protocol.actor import ActorUniqueID
from protocol.common import BlockPos, Color, NetworkBlockPos

package = "bedrock.protocol"


class MapDecorationType(IntEnum):
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


class MapDecoration:
    image: MapDecorationType = field(type=int8)
    rotation: int8
    x: int8
    y: int8
    label: str
    color: Color = field(type=uvarint32)


class MapItemTrackedActor:
    class Type(IntEnum):
        ENTITY = 0
        BLOCK_ENTITY = 1
        OTHER = 2

    class UniqueId:
        type: "MapItemTrackedActor.Type" = field(type=int32)
        key_entity_id: ActorUniqueID = field(when=lambda p: p.type == MapItemTrackedActor.Type.ENTITY)
        key_block_pos: NetworkBlockPos = field(
            when=lambda p: p.type == MapItemTrackedActor.Type.BLOCK_ENTITY, until=944
        )
        key_block_pos: BlockPos = field(when=lambda p: p.type == MapItemTrackedActor.Type.BLOCK_ENTITY, since=944)


@packet(id=67)
class ClientboundMapItemDataPacket:
    class Type(IntFlag):
        TEXTURE_UPDATE = 1 << 1
        DECORATION_UPDATE = 1 << 2
        CREATION = 1 << 3

    map_id: ActorUniqueID  # BDS mMapIds[0] / mapId. Wire is varint64.
    type: Type = field(type=uvarint32)
    dimension_id: uint8
    locked: bool = field(since=354)
    map_origin: BlockPos = field(since=544)

    # COMPILER_EXTENSION_NEEDED: the wire `type` flags are COMPUTED from whether
    # each payload block is populated (CloudburstMC sets the CREATION bit iff the
    # tracked-entity list is non-empty, etc). The DSL surface treats `type` as a
    # caller-pinned value, so a caller must set the flags matching the payload
    # blocks they populate; the DSL has no spelling for "this flag is set iff
    # field X is non-empty" on serialize.
    map_ids: list[ActorUniqueID] = field(when=lambda p: p.type & ClientboundMapItemDataPacket.Type.CREATION != 0)
    scale: int8 = field(
        when=lambda p: (
            p.type
            & (
                ClientboundMapItemDataPacket.Type.TEXTURE_UPDATE
                | ClientboundMapItemDataPacket.Type.DECORATION_UPDATE
                | ClientboundMapItemDataPacket.Type.CREATION
            )
            != 0
        )
    )
    tracked_objects: list[MapItemTrackedActor.UniqueId] = field(
        when=lambda p: p.type & ClientboundMapItemDataPacket.Type.DECORATION_UPDATE != 0,
    )
    decorations: list[MapDecoration] = field(
        when=lambda p: p.type & ClientboundMapItemDataPacket.Type.DECORATION_UPDATE != 0,
    )
    with field(when=lambda p: p.type & ClientboundMapItemDataPacket.Type.TEXTURE_UPDATE != 0):
        width: varint32
        height: varint32
        x_offset: varint32
        y_offset: varint32
        pixels: list[uvarint32]


@packet(id=131, since=354)
class MapCreateLockedCopyPacket:
    """This is fired when the user locks a map item utilizing the Cartography Table in game."""

    original_map_id: ActorUniqueID
    new_map_id: ActorUniqueID


@packet(id=68)
class MapInfoRequestPacket:
    """In the case of the client being unable to find map data for a map item it sends a uuid for a map to the
    server."""

    class ClientPixelsProxy:
        pixel: uint32
        index: uint16

    map_id: ActorUniqueID
    client_pixels: list[ClientPixelsProxy] = field(prefix=uint32, since=544)
