"""DSL surface consumed by the bpc compiler."""

from enum import auto
from typing import Any, TypeAliasType, Union

__version__ = 975


def _identity(cls):
    return cls


def value(
    v: int | None = None,
    since: int | None = None,
    until: int | None = None,
    deprecated: int | None = None,
) -> int:
    """Mark a member's wire value, optionally gated by protocol version.

    - `v`: explicit wire value. Omit to auto-number as `previous_member + 1`,
      mirroring `enum.auto()` but allowing the version-gating kwargs below.
      For an auto-numbered member with no other options, prefer plain
      `enum.auto()` -- shorter and more idiomatic.
    - `since`: first protocol version where the member is present (inclusive).
    - `until`: first protocol version where the member is removed (exclusive),
      so the member is present in `[since, until)`.
    - `deprecated`: protocol version where Mojang marked the member deprecated.
      Acts like `until=` but the member stays on the wire: every snapshot from
      this version on emits the value with `[[deprecated("since vN")]]`, so a
      downstream `-Wdeprecated-declarations` build flags any new use.
    """
    return auto() if v is None else v


def field(
    *,
    type: type[str | Union] | TypeAliasType | None = None,
    since: int | None = None,
    until: int | None = None,
    when: Any = None,
    endian: str | None = None,
    prefix: TypeAliasType | None = None,
    count: Any = None,
    tag: TypeAliasType | type | None = None,
) -> Any:
    """Mark a struct field.

    - `type`: the on-the-wire shape. For enum-typed fields, a primitive
      (e.g. `uvarint32`, `varint32`, `str`). For optional fields, defaults
      to a single-byte bool flag + payload; passing `typing.Union` switches
      to a varint union-index discriminator instead. The index follows the
      annotation order, so `X | None` encodes present as 0 / absent as 1,
      while `None | X` encodes present as 1 / absent as 0.
    - `since`: protocol version that introduced the field.
    - `until`: first protocol version where the field is removed (exclusive),
      so the field is present in `[since, until)`. Redeclaring the same field
      name with adjacent `since` / `until` ranges and differing annotations
      models a field whose type or wire shape changed across versions.
    - `when`: a one-argument lambda gating the field on the value of earlier
      fields in the same struct, e.g. `when=lambda p: p.action == Foo.BAR`.
      Unlike `X | None`, nothing marks presence on the wire -- both serialize
      and deserialize recompute it from the predicate, so the field reads as
      `X` but compiles to an optional. The lambda body may use attribute
      access on its parameter, `Enum.MEMBER` literals, integer literals,
      comparisons, `and`/`or`, `not`, and bitwise `&` (handy for testing
      bits in a fixed-width flags field, e.g. `p.flags & FLAG_HAS_X != 0`).
      It may only reference fields declared before this one.
    - `endian`: byte order for a fixed-width primitive or integer-coded enum
      field, `"big"` or `"little"` (the default). Bedrock sends primitives
      little-endian or as varints almost everywhere, the rare exceptions
      being a connection's initial protocol version and the play status.
    - `prefix`: for a `list[T]` or `dict[K, V]` field, the integer primitive
      that length-prefixes the elements on the wire (default `uvarint32`). A
      `list[T]` annotation is a length-prefixed sequence and `dict[K, V]` a
      length-prefixed map of key/value pairs; a `tuple[T, ...]` annotation of
      N identical types is a fixed-length array of exactly N elements and
      carries no prefix. On a bare `bytes` field, `prefix=None` marks the
      field as trailing -- the wire form has no length marker and the frame
      boundary terminates the read. A trailing field must be the last
      field of its struct.
    - `count`: a one-argument lambda whose body is an integer expression
      over earlier fields, e.g. `count=lambda p: p.width * p.height`. Only
      valid on a `list[T]` field. The wire has no length prefix -- both
      serialize and deserialize compute the element count by evaluating the
      expression against the surrounding struct. Setting `count=` suppresses
      the default `prefix=`; passing an explicit `prefix=` together with
      `count=` is an error. The expression may reference earlier fields
      (`p.<name>`), integer literals, and arithmetic operators `*`, `+`,
      `-`. Use this for inline arrays sized by sibling fields (BDS's shaped
      recipe grid, for instance, is `width * height` ingredients with no
      separate count on the wire).
    - `tag`: integer primitive that prefixes the active-case index of a
      multi-case union on the wire (default `uvarint32`). Applies to a
      `T1 | T2 | T3 | ...` annotation, including inline unions inside a
      `list[T1 | T2 | T3]` -- each list element carries its own tag. Has
      no effect on a `T | None` optional. The field's resolved type must
      contain a multi-case union or `tag=` is an error.

      An `IntEnum` is also accepted: the wire form stays `varint32` and
      the enum's members supply the C++ case labels (`EnumName::MEMBER`),
      one-to-one with the union alternatives in declaration order.

    `with field(when=lambda p: ...):` may also be written as a statement in a
    struct body: every field declared inside the block is gated by the shared
    predicate, as if each carried that `when=`. Unlike a per-field `when=`, a
    guard block may enclose optional and union fields.
    """
    return None


def type(
    *,
    since: int | None = None,
    until: int | None = None,
    deprecated: int | None = None,
):
    """Class decorator: version-gate a type. `since=N` is the protocol version
    that introduced it -- the generated type is absent from snapshots below N.
    Applies to an enum or a non-packet struct; a packet carries its own
    `since` on `@packet`.

    A struct may be declared more than once, each declaration carrying an
    adjacent `[since, until)` range, to model a type whose shape changed across
    protocol versions; the compiler merges the declarations into one versioned
    type. `until` is the first protocol version where that declaration's shape
    no longer applies (exclusive). The declarations must be contiguous (each
    `until` equal to the next `since`) and only the last omits `until`. `until`
    is meaningful only on such a redeclared class.

    `deprecated`: the protocol version where Mojang marked the type deprecated.
    The generated type stays emittable (so a `std::variant` index that pins
    the type to a wire-tag value keeps its slot), but the C++ definition
    carries `[[deprecated("since vN")]]` so a downstream
    `-Wdeprecated-declarations` build flags any new use.
    """
    return _identity


def packet(*, id: int, since: int | None = None):
    """Class decorator: mark a struct as a packet.

    - `id`: the on-the-wire packet id.
    - `since`: protocol version that introduced the packet. The generated
      type is absent from snapshots below it.
    """
    return _identity


def builtin(cls):
    """Class decorator: mark a type as a compiler built-in.

    The compiler emits no definition and no serializer for the type. It
    resolves fields of the type by name, routes them through `Serializer<Name>`,
    and trusts a hand-written struct plus `Serializer` specialization in
    `<bedrock/nbt.hpp>`. Use it for wire shapes the DSL cannot express -- see
    protocol/nbt.py, where the twelve NBT tags are declared this way.
    """
    return cls


@builtin
class bitset:
    """A fixed-width `std::bitset<N>` on the wire.

    Spell as `bitset[N]` in a field annotation: the wire form is a base-128
    little-endian dump of the bitset's numeric value (seven payload bits per
    byte, the top bit a continuation flag, with a lone 0x00 byte for the
    empty bitset).
    """

    def __class_getitem__(cls, _n: int):
        return cls


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
