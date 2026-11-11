"""The schema language.

A schema module imports these names and declares structs, packets, type aliases and builtins with
them. The compiler reads the module's source and never runs it, so every call is checked against the
signature written here: a keyword this module does not list is an error.

Every `since` and `until` names a version in the package's `versions`, and a range is `[since, until)`.

A field named after a Python keyword carries one trailing underscore, which the compiler drops
(`pass_` is `pass`). Any other trailing underscore is part of the name.

An enum is `class E(IntEnum, P)` or `class E(Enum, P)`, where P is bool, int8, uint8, int16, uint16,
int32 or uint32 and becomes `enum class E : P`. The bare base `class E(IntEnum)` or `(Enum)` has type
`int`. An enum field goes on the wire as P when P is one byte, and otherwise as varint32 or uvarint32
by the signedness of P. A member is `PEP8_NAME = N`, `= -N`, `= auto()`, `= OTHER` or `= OTHER - k`
for an earlier member, and reaches C++ as `CamelCase`. `auto()` and a `value()` without a number take
the previous present member's value plus one, at each version. A member name may repeat over disjoint
version ranges. The wire name is the pair or else the member name without underscores, folded to
lower case. A member whose BDS spelling differs by more than case is paired with it,
`HIGH_PANTS = 8, "persona_high_pants"`, or `value(8, "persona_high_pants")`.

`X | None` is a presence byte (1 = present), then X. Every other union, `Union[...]` included, is a
uvarint32 index over its cases in declaration order, then the case, with `None` an empty case, so
`Union[T, None]` writes 0 for T. `type X = A | B` names a union that stays one case inside an
enclosing union. `list[T]` and `dict[K, V]` are a uvarint32 count, then the elements or the key and
value pairs. `Literal[True]`, `Literal["s"]` and `Literal[E.M]`, as a field's whole annotation, are a
constant with no C++ member that the write emits and the read requires.
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

    - `v`: the wire value. Omit it to number the member as the previous present member plus one.
    - `name`: BDS's spelling, the same string the pair `MEMBER = 3, "WireName"` gives.
    - `cpp_name`: BDS's casing for an acronym the derived C++ name flattens. Only the casing may differ.
    - `since`: the first protocol version that has the member, within its declaration's range.
    - `until`: the first protocol version that no longer has it, within its declaration's range.

    A gate that its declaration's range already decides is an error.
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
      declaration's range. A gate that the declaration's range already decides is an error.
    - `when`: a one-argument lambda over earlier fields: `p.f`, `not`, `and`, `or`, `==`, `!=`, `<`,
      `&`, `in {E.A, ...}`, `p.bits.test(E.M)`, integers and enum members. Every field it reads is
      present wherever this one is, and every member it names exists there. Nothing marks presence
      on the wire: both directions recompute it, and the field stays the bare type in C++.
    - `endian`: `"big"` for a 16, 32 or 64-bit integer, or an enum whose `type=` is one, written big-endian. `int8`,
      `uint8`, the varints and a primitive alias take none.
    - `prefix`: `uint32`, `uint16` or `varint32` in place of the field's `list`'s `uvarint32` count.
    - `count`: a one-argument lambda that gives a bare `list` its length instead of a prefix: an
      earlier field, `len(p.f)` of an earlier list or dict, or a product of them with `*`. Every
      field it reads is present wherever the list is.
    - `cereal`: `False` reaches the `@type(cereal=False)` declaration of the annotated type. It flows
      through `list`, `dict`, `T | None`, union cases and array elements, and every name it reaches
      needs a `@type(cereal=False)` declaration.

    `with field(when=...):` takes only `when=`, holds only fields, and gates each of them by one
    predicate. A field inside carries no `when=` of its own.
    """
    return None


def type(*, since: int | None = None, until: int | None = None, cereal: bool = True) -> Callable[[Any], Any]:
    """Class decorator: gate a struct or enum by protocol version.

    A type may be declared again with the adjacent range that follows; the declarations form one
    versioned type, and only the last may be open. A nested class lives within its owner's range,
    narrowed by its own gates, and is one type across its owner's redeclarations. `cereal=False`
    marks BDS's hand-written encoding of a type BDS also cerealises; only a reference spelled
    `field(cereal=False)` reaches it.
    """
    return lambda cls: cls


def packet(*, id: int, since: int | None = None, until: int | None = None) -> Callable[[Any], Any]:
    """Class decorator: a struct that is the packet with this id, gated like `type`.

    Every declaration carries the same id, and two packets share an id only over disjoint ranges.
    """
    return lambda cls: cls


def builtin[T](cls: T) -> T:
    """Class decorator: a hand-written type. The compiler emits no definition and calls its `Serializer`."""
    return cls


class bitset:
    """`bitset[E.M]` is a `std::bitset` as wide as the enum member `E.M`, written as a base-128 dump."""


class array:
    """`array[T, N]` is a `std::array` of exactly N elements, written back to back with no prefix.

    It nests: `array[array[int8, 16], 16]`.
    """


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
