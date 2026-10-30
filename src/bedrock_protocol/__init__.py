"""Owned, typed Bedrock protocol values and codecs.

The compiler can be imported before the native runtime has been built.
"""

from collections.abc import Buffer as ReadableBuffer
from importlib import import_module

from ._api import DecodeError, EncodeError, ProtocolError, UnsupportedVersionError

_NATIVE_EXPORTS = (
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
)
_MODULE_EXPORTS = (
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
)
__all__ = [
    *_NATIVE_EXPORTS,
    "ReadableBuffer",
    "ProtocolError",
    "EncodeError",
    "DecodeError",
    "UnsupportedVersionError",
    *_MODULE_EXPORTS,
]


def __getattr__(name):
    if name in _MODULE_EXPORTS:
        result = import_module(f".{name}", __name__)
    elif name in _NATIVE_EXPORTS:
        result = getattr(import_module("._native", __name__), name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = result
    return result
