from collections.abc import Buffer, Iterator
from enum import Enum
from typing import Generic, Self, TypeVar

import bedrock_protocol.v729 as v729
import bedrock_protocol.v748 as v748
import bedrock_protocol.v766 as v766
import bedrock_protocol.v776 as v776
import bedrock_protocol.v786 as v786
import bedrock_protocol.v800 as v800
import bedrock_protocol.v818 as v818
import bedrock_protocol.v819 as v819
import bedrock_protocol.v827 as v827
import bedrock_protocol.v844 as v844
import bedrock_protocol.v859 as v859
import bedrock_protocol.v898 as v898
import bedrock_protocol.v924 as v924
import bedrock_protocol.v944 as v944
import bedrock_protocol.v975 as v975
import bedrock_protocol.v1001 as v1001
import bedrock_protocol.v2168 as v2168
import bedrock_protocol.v2193 as v2193
import bedrock_protocol.v2225 as v2225
import bedrock_protocol.wire as wire

from ._api import DecodeError as DecodeError
from ._api import EncodeError as EncodeError
from ._api import ProtocolError as ProtocolError
from ._api import UnsupportedVersionError as UnsupportedVersionError

__all__ = [
    "Codec",
    "DecodeLimits",
    "DecodedPacket",
    "EncodedPacket",
    "PacketHeader",
    "UnknownPacket",
    "Variant",
    "Value",
    "Packet",
    "BinaryView",
    "SequenceView",
    "MapView",
    "Nbt",
    "NbtType",
    "SUPPORTED_VERSIONS",
    "ReadableBuffer",
    "ProtocolError",
    "EncodeError",
    "DecodeError",
    "UnsupportedVersionError",
    "v729",
    "v748",
    "v766",
    "v776",
    "v786",
    "v800",
    "v818",
    "v819",
    "v827",
    "v844",
    "v859",
    "v898",
    "v924",
    "v944",
    "v975",
    "v1001",
    "v2168",
    "v2193",
    "v2225",
    "wire",
]

ReadableBuffer = Buffer
T = TypeVar("T", covariant=True)
K = TypeVar("K")
V = TypeVar("V", covariant=True)
SUPPORTED_VERSIONS: tuple[int, ...]

class DecodeLimits:
    def __init__(
        self, *, max_decoded_elements: int = 1048576, max_decoded_bytes: int = 67108864, max_depth: int = 128
    ) -> None: ...
    @property
    def max_decoded_elements(self) -> int: ...
    @property
    def max_decoded_bytes(self) -> int: ...
    @property
    def max_depth(self) -> int: ...

class Value:
    @property
    def protocol(self) -> int | None: ...
    def copy(self) -> Self: ...

class Packet(Value):
    packet_id: int

class PacketHeader:
    @property
    def packet_id(self) -> int: ...
    @property
    def sender_subclient_id(self) -> int: ...
    @property
    def target_subclient_id(self) -> int: ...

class DecodedPacket:
    @property
    def protocol(self) -> int: ...
    @property
    def header(self) -> PacketHeader: ...
    @property
    def payload(self) -> Packet: ...

class EncodedPacket:
    @property
    def protocol(self) -> int: ...
    @property
    def packet_id(self) -> int: ...
    def __len__(self) -> int: ...

class Codec:
    def __init__(self, protocol: int, *, limits: DecodeLimits = ...) -> None: ...
    @property
    def protocol(self) -> int: ...
    @property
    def limits(self) -> DecodeLimits: ...
    @property
    def supported_packet_ids(self) -> tuple[int, ...]: ...
    @property
    def known_packet_ids(self) -> tuple[int, ...]: ...
    def decode_packet(self, data: ReadableBuffer) -> DecodedPacket: ...
    def encode_packet(self, packet: Packet, *, sender_subclient_id: int = 0, target_subclient_id: int = 0) -> bytes: ...
    def prepare_packet(
        self, packet: Packet, *, sender_subclient_id: int = 0, target_subclient_id: int = 0
    ) -> EncodedPacket: ...

class BinaryView(Value, Buffer):
    def __buffer__(self, flags: int) -> memoryview: ...
    def __len__(self) -> int: ...
    def __getitem__(self, index: int) -> int: ...
    def to_bytes(self) -> bytes: ...

class UnknownPacket(Packet):
    def __init__(self, *, packet_id: int, body: ReadableBuffer) -> None: ...
    @property
    def body(self) -> BinaryView: ...
    def wire_bytes(self) -> bytes: ...

class SequenceView(Value, Generic[T]):
    def __len__(self) -> int: ...
    def __getitem__(self, index: int) -> T: ...
    def __iter__(self) -> Iterator[T]: ...
    def to_list(self) -> list[object]: ...

class MapView(Value, Generic[K, V]):
    def __len__(self) -> int: ...
    def __getitem__(self, key: K) -> V: ...
    def __iter__(self) -> Iterator[K]: ...
    def to_dict(self) -> dict[K, object]: ...

class Variant(Generic[T]):
    def __init__(self, index: int, value: T) -> None: ...
    @property
    def index(self) -> int: ...
    @property
    def value(self) -> T: ...

class NbtType(Enum):
    END = 0
    BYTE = 1
    SHORT = 2
    INT = 3
    INT64 = 4
    FLOAT = 5
    DOUBLE = 6
    BYTE_ARRAY = 7
    STRING = 8
    LIST = 9
    COMPOUND = 10
    INT_ARRAY = 11

class Nbt(Value, Buffer):
    def __buffer__(self, flags: int) -> memoryview: ...
    def __init__(self, type: NbtType, value: object, *, element_type: NbtType | None = None) -> None: ...
    @property
    def type(self) -> NbtType: ...
    @property
    def element_type(self) -> NbtType | None: ...
    @property
    def value(self) -> int | float | str | None: ...
    def __len__(self) -> int: ...
    def __getitem__(self, key: str | int) -> Nbt | int: ...
    def __iter__(self) -> Iterator[str | Nbt | int]: ...
    def to_bytes(self) -> bytes: ...
    def to_dict(self) -> dict[str, object]: ...
    def wire_bytes(self) -> bytes: ...
