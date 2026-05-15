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
) -> Any:
    """Mark a struct field.

    - `type`: the on-the-wire shape. For enum-typed fields, a primitive
      (e.g. `uvarint32`, `varint32`, `str`). For `X | None` fields, defaults
      to a single-byte bool flag + payload; passing `typing.Union` switches
      to a varint discriminator (`0` = present, `1` = None) instead.
    - `since`: protocol version that introduced the field.
    - `endian`: byte order for a fixed-width primitive or integer-coded enum
      field, `"big"` or `"little"` (the default). Bedrock sends primitives
      little-endian or as varints almost everywhere, the rare exceptions
      being a connection's initial protocol version and the play status.
    """
    return None


def enum(*, since: int | None = None):
    """Class decorator: attach metadata to the type (e.g. `since=N`)."""
    return _identity


def packet(*, id: int):
    """Class decorator: mark a struct as a packet with on-the-wire id."""
    return _identity
