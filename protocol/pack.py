"""Resource and behaviour packs: Core/Resource/ and engine/PackInfrastructure --
pack identity, versions, the download handshake, the applied stack, pack settings."""

import uuid
from enum import Enum, IntEnum, auto

from protocol import field, int8, int32, packet, uint16, uint32, uint64
from protocol.game import Experiments

package = "bedrock.protocol"


class SemVersion:
    version: str


class ContentIdentity:
    identity: str


class PackIdVersion:
    id: uuid.UUID
    version: SemVersion


class PackInfoData:
    pack_id_version: PackIdVersion
    pack_size: uint64
    content_key: str
    subpack_name: str
    content_identity: ContentIdentity
    has_scripts: bool
    is_addon_pack: bool
    is_ray_tracing_capable: bool
    cdn_url: str


class ResourcePackResponse(Enum, int8):
    CANCEL = 1
    DOWNLOADING = 2
    DOWNLOADING_FINISHED = 3
    RESOURCE_PACK_STACK_FINISHED = 4


@packet(id=6, until=2168)
class ResourcePacksInfoPacket:
    """The packs the client has to have before it may join, each named by uuid and
    version so the client can serve one it already cached."""

    resource_pack_required: bool
    has_addon_packs: bool
    has_scripts: bool
    force_disable_vibrant_visuals: bool
    world_template_id_and_version: PackIdVersion
    resource_packs: list[PackInfoData] = field(prefix=uint16)


@packet(id=6, since=2168)
class ResourcePacksInfoPacket:
    resource_pack_required: bool
    has_addon_packs: bool
    has_scripts: bool
    force_disable_vibrant_visuals: bool
    world_template_id_and_version: PackIdVersion
    resource_packs: list[PackInfoData]


@packet(id=8, until=2168)
class ResourcePackClientResponsePacket:
    """The client's step in the pack handshake: which packs it still wants, then
    twice more to say the download and the stack are done."""

    response: ResourcePackResponse
    downloading_packs: list[str] = field(prefix=uint16)


@packet(id=8, since=2168)
class ResourcePackClientResponsePacket:
    class Cancel:
        response_type: ResourcePackResponse = field(type=str)

    class Downloading:
        response_type: ResourcePackResponse = field(type=str)
        downloading_packs: list[str]

    class DownloadingFinished:
        response_type: ResourcePackResponse = field(type=str)

    class ResourcePackStackFinished:
        response_type: ResourcePackResponse = field(type=str)

    response: Cancel | Downloading | DownloadingFinished | ResourcePackStackFinished


@packet(id=329, until=2192)
class ServerboundPackSettingChangePacket:
    pack_id: uuid.UUID
    pack_setting_name: str
    pack_setting_value: float | bool | str


@packet(id=329, since=2192)
class ServerboundPackSettingChangePacket:
    pack_id: uuid.UUID
    pack_setting_name: str
    pack_setting_value: float | bool | str | list[str]


class PackInstanceId:
    pack_id: str
    version: str
    subpack_name: str


@packet(id=7)
class ResourcePackStackPacket:
    """The order the client applies the accepted texture packs in, with the base game
    version its stack falls back to and the experiments the world runs."""

    texture_pack_required: bool
    texture_pack_ids_and_versions: list[PackInstanceId]
    base_game_version: str
    experiments: Experiments
    include_editor_packs: bool


class PackType(IntEnum, int8):
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
    """The header for one pack's download: how its bytes will be chunked, how large the
    archive is, and the hash the client checks the reassembled file against."""

    resource_name: str
    chunk_size: uint32
    nb_chunks: uint32
    file_size: uint64
    file_hash: str
    is_premium: bool
    pack_type: PackType


@packet(id=83)
class ResourcePackChunkDataPacket:
    """One chunk of a pack the client is downloading: the pack the chunk belongs to,
    the chunk's index in the sequence, and its offset into the pack file."""

    resource_name: str
    chunk_id: uint32
    byte_offset: uint64
    data: bytes


@packet(id=84, until=2168)
class ResourcePackChunkRequestPacket:
    resource_name: str
    chunk: uint32


@packet(id=84, since=2168)
class ResourcePackChunkRequestPacket:
    resource_name: str
    chunk: int32


@packet(id=340, since=944)
class ResourcePacksReadyForValidationPacket:
    pass
