"""Bedrock packet types: the bare names are the latest protocol's, `v<N>` holds protocol N's codec and older types."""

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


__all__ = [
    "ProtocolVersion",
    "nbt",
    "protocol_version",
    "releases",
    "versions",
    *(name for name, value in globals().items() if isinstance(value, type) and value.__module__ == __name__),
]
