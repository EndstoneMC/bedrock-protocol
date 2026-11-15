"""Bedrock packet types: the bare names are the latest protocol, `v<N>` pins one and holds its codec."""

from importlib import import_module

from ._core import ProtocolVersion, protocol_version, releases, versions


class DecodeError(ValueError):
    """Bytes that do not decode as the type asked for."""

    def __init__(self, message: str, reason: str, path: tuple[str | int, ...], offset: int) -> None:
        super().__init__(message)
        self.reason = reason
        self.path = path
        self.offset = offset

    def __reduce__(self) -> tuple[type[ValueError], tuple[str, str, tuple[str | int, ...], int]]:
        return type(self), (str(self), self.reason, self.path, self.offset)


class EncodeError(ValueError):
    """A value its encoding cannot write."""

    def __init__(self, message: str, reason: str, path: tuple[str | int, ...]) -> None:
        super().__init__(message)
        self.reason = reason
        self.path = path

    def __reduce__(self) -> tuple[type[ValueError], tuple[str, str, tuple[str | int, ...]]]:
        return type(self), (str(self), self.reason, self.path)


_latest = import_module(f".v{versions[-1]}", __name__)
_types = {name: getattr(_latest, name) for name in _latest.__all__ if isinstance(getattr(_latest, name), type)}
globals().update(_types)
__all__ = [
    "DecodeError",
    "EncodeError",
    "PacketHeader",
    "ProtocolVersion",
    "SerializationMode",
    "nbt",
    "protocol_version",
    "releases",
    "versions",
    *_types,
]
del import_module, _latest, _types
