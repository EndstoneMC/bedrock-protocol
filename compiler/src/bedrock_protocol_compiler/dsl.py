"""The schema language: the compiler reads a schema module's source and never runs it.

`since` and `until` name versions and give the range `[since, until)`.
A field named after a Python keyword carries one trailing underscore, which the compiler drops (`pass_`).
"""

from collections.abc import Callable
from typing import Any


def value(
    v: int | None = None,
    name: str | None = None,
    /,
    *,
    cpp_name: str | None = None,
    since: int | None = None,
    until: int | None = None,
) -> int:
    """Mark an enum member's wire value, optionally with BDS's spelling or a version gate."""
    return 0 if v is None else v


def field(
    *,
    type: Any = None,
    since: int | None = None,
    until: int | None = None,
    when: Any = None,
    endian: str | None = None,
    prefix: Any = None,
    count: Any = None,
    cereal: bool = True,
) -> Any:
    """Mark a struct field: a wire override, a version gate, or a condition over earlier fields."""
    return None


def type(*, since: int | None = None, until: int | None = None, cereal: bool = True) -> Callable[[Any], Any]:
    """Class decorator: gate a struct or enum by protocol version."""
    return lambda cls: cls


def packet(*, id: int, since: int | None = None, until: int | None = None) -> Callable[[Any], Any]:
    """Class decorator: a struct that is the packet with this id."""
    return lambda cls: cls


def builtin[T](cls: T) -> T:
    """Class decorator: a hand-written type whose `Serializer` the compiler calls."""
    return cls


class bitset:
    """`bitset[E.M]` is a `std::bitset` as wide as the enum member `E.M`."""


class array:
    """`array[T, N]` is a `std::array` of N elements with no length prefix."""


type varint32 = int
type varint64 = int
type uvarint32 = int
type uvarint64 = int
type int8 = int
type int16 = int
type int32 = int
type int64 = int
type uint8 = int
type uint16 = int
type uint32 = int
type uint64 = int
type double = float
