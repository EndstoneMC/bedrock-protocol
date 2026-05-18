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
    """
    return None


def enum(*, since: int | None = None):
    """Class decorator: attach metadata to the type (e.g. `since=N`)."""
    return _identity


def packet(*, id: int, since: int | None = None):
    """Class decorator: mark a struct as a packet.

    - `id`: the on-the-wire packet id.
    - `since`: protocol version that introduced the packet. The generated
      type is absent from snapshots below it.
    """
    return _identity
