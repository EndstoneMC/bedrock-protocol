"""Bedrock packets and codecs: the bare names are the latest protocol, `v<N>` pins one."""

from importlib import import_module

from ._core import VERSIONS


class DecodeError(ValueError):
    """Bytes that do not decode as the type asked for."""

    def __init__(self, message: str, reason: str, path: tuple[str | int, ...], offset: int) -> None:
        super().__init__(message)
        self.reason = reason
        self.path = path
        self.offset = offset

    def __reduce__(self) -> tuple[type[ValueError], tuple[str, str, tuple[str | int, ...], int]]:
        return type(self), (str(self), self.reason, self.path, self.offset)


_latest = import_module(f".v{VERSIONS[-1]}", __name__)
globals().update({name: getattr(_latest, name) for name in dir(_latest) if not name.startswith("_")})
del import_module, _latest
