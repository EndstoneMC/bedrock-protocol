import uuid
from enum import IntEnum, auto

from protocol import field, int32, packet, type, uint8, uint16, uint32, uint64
from protocol.game import Experiments

package = "bedrock.protocol"


@packet(id=83)
class ResourcePackChunkDataPacket:
    """(only one marked for uncompressed) realms resource pack download."""

    resource_name: str
    chunk_id: int32
    byte_offset: uint64
    data: bytes = field(prefix=uint32)


@packet(id=84)
class ResourcePackChunkRequestPacket:
    """Resource Pack Chunk Request."""

    resource_name: str
    chunk: int32


class ResourcePackResponse(IntEnum):
    CANCEL = 1
    DOWNLOADING = 2
    DOWNLOADING_FINISHED = 3
    RESOURCE_PACK_STACK_FINISHED = 4


@packet(id=8)
class ResourcePackClientResponsePacket:
    response: ResourcePackResponse = field(type=uint8)
    downloading_packs: list[str] = field(prefix=uint16)


@type(since=361)
class PackType(IntEnum):
    INVALID = 0
    ADDON = 1
    CACHED = 2
    COPY_PROTECTED = 3
    BEHAVIOR = 4
    PERSONA_PIECE = 5
    RESOURCES = 6
    SKINS = 7
    WORLD_TEMPLATE = 8
    COUNT = auto()


@packet(id=82)
class ResourcePackDataInfoPacket:
    """Sent from the serverFileChunkUploader during the initialization of the
    file uploader. This packet is sent to the primary client."""

    resource_name: str
    chunk_size: uint32
    nb_chunks: uint32
    file_size: uint64
    file_hash: str
    is_premium: bool = field(since=361)
    pack_type: PackType = field(type=uint8, since=361)


# BDS: PackInstanceId. BDS stores mPackId as PackIdVersion, but the wire flattens
# the id and version to two separate strings.
class PackInstanceId:
    pack_id: str
    pack_version: str
    sub_pack_name: str


@packet(id=7)
class ResourcePackStackPacket:
    """Sent to client in response to ResourcePackClientResponsePacket with info
    on current resource pack stack."""

    texture_pack_required: bool  # mTexturePackRequired
    # v291..v898 wrote the behavior-pack stack ahead of the texture-pack stack; v898
    # dropped the behavior list entirely.
    behavior_packs: list[PackInstanceId] = field(until=898)
    texture_packs: list[PackInstanceId]
    # v313..v419 wrote a lone boolean that stood in for the experiments table that
    # arrived in v419.
    experiments_legacy_v313: bool = field(since=313, until=419)
    base_game_version: str = field(since=388)  # mBaseGameVersion
    experiments: Experiments = field(since=419)
    experiments_previously_toggled: bool = field(since=419)
    include_editor_packs: bool = field(since=671)


# BDS: PackInfoData (an element of PacksInfoData::mResourcePacks). mHasExceptions
# exists in BDS but never appears on the wire.
class PackInfoData:
    pack_id: str = field(until=766)
    pack_id: uuid.UUID = field(since=766)
    pack_version: str
    pack_size: uint64
    content_key: str
    sub_pack_name: str
    content_identity: str
    has_scripts: bool = field(since=332)
    is_addon_pack: bool = field(since=712)
    is_ray_tracing_capable: bool = field(since=422)
    cdn_url: str = field(since=748)


@packet(id=6)
class ResourcePacksInfoPacket:
    resource_pack_required: bool
    has_addon_packs: bool = field(since=662)
    has_scripts: bool = field(since=332)
    force_disable_vibrant_visuals: bool = field(since=818)
    world_template_id: uuid.UUID = field(since=766)
    world_template_version: str = field(since=766)
    forcing_server_packs_enabled: bool = field(since=448, until=729)
    # v291..v729 wrote behavior packs before resource packs; v729 dropped them.
    # The list is uint16_le-length-prefixed.
    behavior_packs: list[PackInfoData] = field(prefix=uint16, until=729)
    resource_packs: list[PackInfoData] = field(prefix=uint16)
    # COMPILER_EXTENSION_NEEDED: from v618 until v748 the wire carried a uvarint32-length-
    # prefixed appendix of (pack_id_string + "_" + pack_version_string, cdn_url) pairs
    # that the codec folded back into each pack's cdn_url. No DSL form models a list
    # whose elements are derived from another list and merged back into a sibling list.
    # At v748 the CDN URL moved into the PackInfoData entry itself (modeled above).
    cdn_entries_v618_v748_placeholder: bool = field(since=618, until=748)


@packet(id=340, since=944)
class ResourcePacksReadyForValidationPacket:
    """Used to inform the server that the client has finished loading all
    resource packs."""
