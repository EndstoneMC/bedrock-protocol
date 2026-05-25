import uuid
from enum import IntEnum

from protocol import field, packet, type, uint8, uint32, uvarint32, varint32
from protocol.common import BlockPos

package = "bedrock.protocol"


# ClientboundDataStorePacket (id=330, since=898) and ServerboundDataStorePacket
# (id=332, since=898) are omitted: the data-store value type
# (Bedrock::DDUI::DataStorePropertyValue) is recursive -- a MAP variant carries
# a list of key/value pairs whose values are themselves DataStorePropertyValue
# -- and the DSL has no spelling for a recursive struct nested inside a tagged
# union today. The ids stay allocated but unused on v975 until the compiler
# grows that spelling.


@packet(id=310, since=686)
class ClientboundCloseFormPacket:
    """Sent from the server to client to force close all server forms on the stack and return to the HUD screen."""

    pass


@packet(id=334, since=924)
class ClientboundDataDrivenUICloseScreenPacket:
    """Allows the server to tell the client to close Data Driven UI screens."""

    form_id: uint32 | None = field(since=944)


@packet(id=335, since=924)
class ClientboundDataDrivenUIReloadPacket:
    """Allows the server to tell the client to reload the Data Driven UI."""

    pass


@packet(id=333, since=924)
class ClientboundDataDrivenUIShowScreenPacket:
    """Allows the server to tell the client to show a Data Driven UI screen."""

    screen_id: str
    form_id: uint32 = field(since=944)
    data_instance_id: uint32 | None = field(since=944)


# bedrock-headers android/r26_u2 declares this id as ClientboundLoadingScreenPacket_Deprecated
# in MinecraftPacketIds. Neither CloudburstMC, gophertunnel, nor EndstoneMC/protocol-docs
# carries a body for it -- the id is allocated but the packet is no longer serialized. The
# loading-screen flow is now driven by ServerboundLoadingScreenPacket (id=312) plus the
# ChangeDimensionPacket.loading_screen_id field added at v712. Empty stub kept so the id
# is not silently absent from the v975 enum surface.
@packet(id=311)
class ClientboundLoadingScreenPacket:
    pass


@packet(id=100)
class ModalFormRequestPacket:
    """Not sent from vanilla. The feature is meant for third-party servers to be able to drive dynamic ui forms. The request comes with some JSON that describes a custom UI screen thirdparty uses. Server->client."""

    form_id: uvarint32
    form_json: str


class ModalFormCancelReason(IntEnum):
    USER_CLOSED = 0
    USER_BUSY = 1


@packet(id=101)
class ModalFormResponsePacket:
    """Fired in response to third party server request to show the custom UI screen."""

    form_id: uvarint32
    json_response: str = field(until=544)
    json_response: str | None = field(since=544)
    form_cancel_reason: ModalFormCancelReason | None = field(type=uint8, since=544)


@packet(id=303, since=582)
class OpenSignPacket:
    """Sent from the server so that the client knows to open the sign screen."""

    pos: BlockPos
    is_front_side: bool


class DataDrivenScreenClosedReason(IntEnum):
    PROGRAMMATIC_CLOSE = 0
    PROGRAMMATIC_CLOSE_ALL = 1
    CLIENT_CANCELED = 2
    USER_BUSY = 3
    INVALID_FORM = 4


@packet(id=343, since=944)
class ServerboundDataDrivenScreenClosedPacket:
    """Sent from the client to the server when a data driven screen is closed."""

    form_id: uint32
    close_reason: DataDrivenScreenClosedReason = field(type=str)


@type(since=712)
class ServerboundLoadingScreenPacketType(IntEnum):
    UNKNOWN = 0
    START_LOADING_SCREEN = 1
    END_LOADING_SCREEN = 2


@packet(id=312, since=712)
class ServerboundLoadingScreenPacket:
    """Sent from the client to the server to message to the server about the state of the loading screen."""

    type: ServerboundLoadingScreenPacketType = field(type=varint32)
    loading_screen_id: uint32 | None


@packet(id=329, since=844)
class ServerboundPackSettingChangePacket:
    """Sent from the client to the server when players change Pack Settings (pack UI)."""

    pack_id: uuid.UUID
    setting_name: str
    setting_value: float | bool | str


@packet(id=186, since=527)
class ToastRequestPacket:
    """Pushes a UI toast message to be displayed by the client."""

    title: str
    content: str
