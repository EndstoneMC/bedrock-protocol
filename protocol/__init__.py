"""DSL surface consumed by the bpc compiler.

A field name may carry a single trailing underscore to escape a Python keyword
(PEP 8's `pass_`); the compiler drops it, so the wire and the generated C++ keep
the BDS name.

An enum member may pair its value with the exact string BDS writes,
`DOWNLOADING_FINISHED = 3, "DownloadingFinished"`, the way `enum.Enum` spells
`MONDAY = 1, "Mon"`. A name-coded enum otherwise reaches the wire as the
member's own spelling: casing is free, since BDS lowercases before the lookup,
but the separator is not, so a PEP 8 member whose BDS name carries none would
both reject BDS's own string and put an extra byte behind the length prefix.
The pair needs a plain `Enum` base, since `IntEnum` and `StrEnum` coerce a
member to their own type and a pair is not one; a member spelled `value()`
takes the string as its second positional instead.

A `typing.Literal[V, ...]` field is a constant the wire carries and the C++
does not: no member is generated, the write emits the first value, and the read
rejects anything the annotation does not list. Bools take the one-byte wire on
their own; an integer literal needs `field(type=<integer primitive>)` for its
width. Use it where BDS writes a fixed byte nobody models -- cereal prefixes a
dynamic member with an always-true member-present marker, so an optional member
reads `_unused: Literal[True]` then `x: T | None`.
"""

from enum import auto
from typing import Any, TypeAliasType, Union

__version__ = 2168


def _identity(cls):
    return cls


def value(
    v: int | None = None,
    name: str | None = None,
    since: int | None = None,
    until: int | None = None,
) -> int:
    """Mark a member's wire value, optionally gated by protocol version.

    - `v`: explicit wire value. Omit to auto-number as `previous_member + 1`,
      mirroring `enum.auto()` but allowing the version-gating kwargs below.
      For an auto-numbered member with no other options, prefer plain
      `enum.auto()` -- shorter and more idiomatic.
    - `name`: the string BDS writes, for a member a plain `Enum` would spell
      `MEMBER = 3, "WireName"`. Spelled here so the escape reaches an `IntEnum`
      or `StrEnum` member, which cannot carry a pair.
    - `since`: first protocol version where the member is present (inclusive).
    - `until`: first protocol version where the member is removed (exclusive),
      so the member is present in `[since, until)`.

    An enum whose members were renumbered is redeclared over adjacent ranges,
    like a reshaped struct; `since` / `until` here cover a member simply
    arriving or going inside one range.
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
    snapshot: int | None = None,
) -> Any:
    """Mark a struct field.

    - `type`: the on-the-wire shape. An enum-typed field defaults to its enum's
      underlying type, compressed to a varint above one byte; pass `type=str`
      for a name-coded enum, or a fixed primitive where BDS does not compress.
      An enum with neither an underlying base nor `type=` is an error.
      For an integer-primitive-typed
      field, an *integer* primitive that overrides the wire encoding while
      the annotation keeps owning the in-memory type -- `y: int32 = field(type=uvarint32)`
      gives `std::int32_t y` in C++ but reads / writes Y as `varint<uint32_t>`
      with a `static_cast` at the boundary (used for `NetworkBlockPos`,
      where BDS keeps Y as `int` but the wire writes it unsigned). For
      optional fields, defaults to a single-byte bool flag + payload;
      passing `typing.Union` switches to a varint union-index discriminator
      instead. The index follows the annotation order, so `X | None` encodes
      present as 0 / absent as 1, while `None | X` encodes present as 1 /
      absent as 0.
    - `since`: protocol version that introduced the field.
    - `until`: first protocol version where the field is removed (exclusive),
      so the field is present in `[since, until)`. These gate a field that is
      simply absent over part of the range; a field whose *type* moved is a
      reshape, and the class is redeclared over adjacent ranges instead (see
      `type` and `packet`).
    - `when`: a one-argument lambda gating the field on the value of earlier
      fields in the same struct, e.g. `when=lambda p: p.action == Foo.BAR`.
      Unlike `X | None`, nothing marks presence on the wire -- both serialize
      and deserialize recompute it from the predicate, so the field reads as
      `X` but compiles to an optional. The lambda body may use attribute
      access on its parameter, `Enum.MEMBER` literals, integer literals,
      comparisons, set-membership against a `{...}` literal (`p.x in {Foo.A,
      Foo.B}`, desugaring to an `or` chain of `==`; `not in` to an `and`
      chain of `!=`), `and`/`or`, `not`, and bitwise `&` (handy for testing
      bits in a fixed-width flags field, e.g. `p.flags & FLAG_HAS_X != 0`).
      It may only reference fields declared before this one. `len(p.xs)` of an
      earlier list, map or string is allowed, as is `p.flags.test(<bit>)` on an
      earlier `bitset[N]` field, where the bit is an integer literal or an
      `Enum.MEMBER`.
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
      valid on a `list[T]` field, or on a `list[T] | None` whose presence
      flag is a separate matter. The wire has no length prefix -- both
      serialize and deserialize compute the element count by evaluating the
      expression against the surrounding struct. Setting `count=` suppresses
      the default `prefix=`; passing an explicit `prefix=` together with
      `count=` is an error. The expression may reference earlier fields
      (`p.<name>`), `len(p.<name>)` of an earlier list, map or string,
      integer literals, and arithmetic operators `*`, `+`, `-`. Use this for
      inline arrays sized by sibling fields (BDS's shaped recipe grid, for
      instance, is `width * height` ingredients with no separate count on the
      wire) and for parallel runs sharing one count (`len(p.entries)`).
    - `snapshot`: resolve this field's struct or enum reference at the given
      protocol version instead of the declaring context's. BDS cerealised
      packets one at a time, so one class name meant two wire shapes at one
      version, chosen by whichever packet contained it: at 1001 packet 30
      carries the cerealised `ItemUseInventoryTransaction` while packet 144
      carries the pre-cereal one. Where BDS gave the two forms separate names
      they are separate declarations; where it reused the name, the older shape
      is still declared over the era before the migration and this is what
      reaches it -- `field(snapshot=975)`. Pins through a `T | None` or
      `list[T]` to the reference inside.

    A `T1 | T2 | T3` union carries no `tag=`: it is always prefixed on the wire
    by a `uvarint32` index over its cases in declaration order. An
    enum-discriminated union is not implemented -- declare the discriminator as
    a real field and gate each arm on it with `when=`.

    Any keyword this signature does not list is a compile error, as is one the
    compiler does not read. It never silently drops one.

    `with field(when=lambda p: ...):` may also be written as a statement in a
    struct body: every field declared inside the block is gated by the shared
    predicate, as if each carried that `when=`. Unlike a per-field `when=`, a
    guard block may enclose optional and union fields, and it takes no keyword
    but `when=`.
    """
    return None


def type(
    *,
    since: int | None = None,
    until: int | None = None,
):
    """Class decorator: version-gate a type. `since=N` is the protocol version
    that introduced it -- the generated type is absent from snapshots below N,
    so a reference from an earlier era has to name the snapshot namespace.
    Applies to an enum or a non-packet struct; a packet carries its own
    `since` on `@packet`.

    A struct or an enum may be declared more than once, each declaration
    carrying an adjacent `[since, until)` range, to model a type whose shape
    changed across protocol versions; the compiler merges the declarations into
    one versioned type. For an enum that means a renumbering: each body holds
    its era's values, a member that moved appears in both, and one that went
    away simply stops. Every declaration of an enum shares one underlying type.
    `until` is the first protocol version where that declaration's shape no
    longer applies (exclusive). The declarations must be contiguous (each
    `until` equal to the next `since`) and only the last omits `until`.
    """
    return _identity


def packet(*, id: int, since: int | None = None, until: int | None = None):
    """Class decorator: mark a struct as a packet.

    - `id`: the on-the-wire packet id.
    - `since`: protocol version that introduced the packet. The generated
      type is absent from snapshots below it.
    - `until`: first protocol version where this declaration's shape no
      longer applies (exclusive). Meaningful only on a redeclared packet,
      where the same `@packet(id=N)` class name appears more than once with
      adjacent `[since, until)` ranges to model a shape change across
      versions, mirroring the `@type(since=, until=)` form. Every
      redeclaration must share the same `id`, and only the last omits
      `until`.
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
