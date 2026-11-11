"""The schema language.

A schema module imports these names and declares structs, packets, type aliases and builtins with
them. The compiler reads the module's source and never runs it, so every call is checked against the
signature written here: a keyword this module does not list is an error.

A field named after a Python keyword carries one trailing underscore, which the compiler drops
(`pass_` is `pass`). Any other trailing underscore is part of the name.

An enum is `class E(IntEnum, P)` or `class E(Enum, P)`, where P is bool, int8, uint8, int16, uint16,
int32 or uint32 and becomes `enum class E : P`. A member is `PEP8_NAME = N`, `= -N`, `= auto()`,
`= OTHER` or `= OTHER - k` for an earlier member, and reaches C++ as `CamelCase`. A member name may
repeat over disjoint version ranges. The wire folds the C++ spelling to lower case, so a member
whose BDS spelling differs by more than case is paired with it, `HIGH_PANTS = 8, "persona_high_pants"`,
or `value(8, "persona_high_pants")`.
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
    """Mark an enum member's wire value, optionally gated by protocol version.

    - `v`: the wire value. Omit it to number the member as the previous member plus one.
    - `name`: the string BDS writes, for a member a plain `Enum` would spell `MEMBER = 3, "WireName"`.
    - `cpp_name`: BDS's casing for an acronym the derived C++ name flattens. Only the casing may differ.
    - `since`: the first protocol version that has the member.
    - `until`: the first protocol version that no longer has it.
    """
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
    """Mark a struct field.

    - `type`: the wire form where it differs from the annotation. `str` name-codes an enum, and an
      integer primitive overrides the wire of an integer field or enum while C++ keeps the
      annotated type. It reaches through `list` and `T | None`, and the one scalar half of a `dict`.
    - `since`, `until`: the field exists in protocol versions `[since, until)`, within its
      declaration's range.
    - `when`: a one-argument lambda over earlier fields. Nothing marks presence on the wire: both
      directions recompute it, and the field stays the bare type in C++.
    - `endian`: `"big"` for a fixed-width integer written big-endian.
    - `prefix`: the integer primitive that prefixes a `list`, `uvarint32` by default.
    - `count`: a one-argument lambda that gives a bare `list` its length instead of a prefix.
    - `cereal`: `False` reaches the `@type(cereal=False)` declaration of the annotated type. It flows
      through `list`, `dict` and `T | None`.

    `with field(when=...):` gates every field in the block by one predicate.
    """
    return None


def type(*, since: int | None = None, until: int | None = None, cereal: bool = True) -> Callable[[Any], Any]:
    """Class decorator: gate a struct or enum by protocol version.

    A type may be declared again with the adjacent range that follows; the declarations form one
    versioned type. `cereal=False` marks BDS's hand-written encoding of a type BDS also cerealises;
    only a reference spelled `field(cereal=False)` reaches it.
    """
    return lambda cls: cls


def packet(*, id: int, since: int | None = None, until: int | None = None) -> Callable[[Any], Any]:
    """Class decorator: a struct that is the packet with this id, gated like `type`."""
    return lambda cls: cls


def builtin[T](cls: T) -> T:
    """Class decorator: a hand-written type. The compiler emits no definition and calls its `Serializer`."""
    return cls


class bitset:
    """`bitset[E.M]` is a `std::bitset` as wide as the enum member `E.M`, written as a base-128 dump."""


class array:
    """`array[T, N]` is a `std::array` of exactly N elements, written back to back with no prefix."""


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
