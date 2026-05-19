"""DSL helpers consumed by the bpc compiler.

griffe reads these statically; at runtime they're intentional no-ops.
"""

from typing import Any, TypeAliasType, Union


def _identity(cls):
    return cls


def value(v, since: int | None = None, until: int | None = None):
    """Mark a member's wire value, optionally gated by protocol version.

    - `since`: first protocol version where the member is present (inclusive).
    - `until`: first protocol version where the member is removed (exclusive),
      so the member is present in `[since, until)`.
    """
    return v


def field(
    *,
    type: type[str | Union] | TypeAliasType | None = None,
    since: int | None = None,
    until: int | None = None,
    when: Any = None,
    endian: str | None = None,
    prefix: TypeAliasType | None = None,
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
      comparisons, `and`/`or`, and `not`. It may only reference fields
      declared before this one.
    - `endian`: byte order for a fixed-width primitive or integer-coded enum
      field, `"big"` or `"little"` (the default). Bedrock sends primitives
      little-endian or as varints almost everywhere, the rare exceptions
      being a connection's initial protocol version and the play status.
    - `prefix`: for a `list[T]` or `dict[K, V]` field, the integer primitive
      that length-prefixes the elements on the wire (default `uvarint32`). A
      `list[T]` annotation is a length-prefixed sequence and `dict[K, V]` a
      length-prefixed map of key/value pairs; a `tuple[T, ...]` annotation of
      N identical types is a fixed-length array of exactly N elements and
      carries no prefix.

    `with field(when=lambda p: ...):` may also be written as a statement in a
    struct body: every field declared inside the block is gated by the shared
    predicate, as if each carried that `when=`. Unlike a per-field `when=`, a
    guard block may enclose optional and union fields.
    """
    return None


def type(*, since: int | None = None, until: int | None = None):
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
