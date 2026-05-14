"""DSL helpers consumed by the bpc compiler.

griffe reads these statically; at runtime they're intentional no-ops.
"""

from typing import Any, TypeAliasType


def value(v, since: int | None = None):
    """Mark a member's wire value, optionally gated by protocol version."""
    return v


def field(*, type: type | TypeAliasType | None = None, since: int | None = None) -> Any:
    """Mark a struct field.

    - `type`: the on-the-wire primitive (e.g. `uvarint32`, or `str` for the
      Bedrock default string-encoded enum). Required for enum-typed fields
      where the annotation alone doesn't fix encoding.
    - `since`: protocol version that introduced the field.
    """
    return None


def enum(*, since: int | None = None):
    """Class decorator: attach metadata to the type (e.g. `since=N`)."""

    def _identity(cls):
        return cls

    return _identity
