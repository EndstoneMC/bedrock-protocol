"""Runtime support independent of the native compiler bootstrap."""

from enum import IntEnum
from typing import Callable, cast


class ProtocolError(Exception):
    def __init__(
        self,
        message: str,
        *,
        protocol: int | None = None,
        packet_id: int | None = None,
        offset: int | None = None,
        reason: str | None = None,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.protocol = protocol
        self.packet_id = packet_id
        self.offset = offset
        self.reason = reason
        self.field = field


class EncodeError(ProtocolError):
    pass


class DecodeError(ProtocolError):
    pass


class UnsupportedVersionError(ProtocolError):
    pass


def _open_enum(name: str, members: dict[str, int], minimum: int, maximum: int, module: str) -> type[IntEnum]:
    factory = cast(Callable[..., type[IntEnum]], IntEnum)
    cls = factory(name, members, module=module)

    def _missing_(enum: type[IntEnum], value: object) -> IntEnum:
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError(f"{name} value is outside its underlying range")
        member = int.__new__(enum, value)
        object.__setattr__(member, "_name_", None)
        object.__setattr__(member, "_value_", value)
        return member

    setattr(cls, "_missing_", classmethod(_missing_))
    return cls
