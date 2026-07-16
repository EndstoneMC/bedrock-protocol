from enum import IntEnum

from protocol import field, packet, uint64

package = "bedrock.protocol"


class SoundDataEvent(IntEnum):
    STOP = 0


class ServerSoundHandle:
    value: uint64


@packet(id=348, since=1001)
class ClientboundUpdateSoundDataPacket:
    server_sound_handle: ServerSoundHandle
    sound_event: SoundDataEvent = field(type=str)
