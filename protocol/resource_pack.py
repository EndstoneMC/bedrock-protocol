import uuid
from enum import Enum

from protocol import field, int8, packet, uint16, uint64

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
    CANCEL = 1, "Cancel"
    DOWNLOADING = 2, "Downloading"
    DOWNLOADING_FINISHED = 3, "DownloadingFinished"
    RESOURCE_PACK_STACK_FINISHED = 4, "ResourcePackStackFinished"


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
    """The packs the client has to have before it may join, each named by uuid and
    version so the client can serve one it already cached."""

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
    """The client's step in the pack handshake: which packs it still wants, then
    twice more to say the download and the stack are done."""

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
