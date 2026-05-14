"""DSL helpers consumed by the bpc compiler.

griffe reads these statically; at runtime they're intentional no-ops.
"""

from typing import Any


def value(v, since: int | None = None):
    """Mark a member's wire value, optionally gated by protocol version."""
    return v


def field(*, since: int | None = None) -> Any:
    """Mark a struct field, optionally gated by protocol version."""
    return None


def enum(*, since: int | None = None):
    """Class decorator: attach metadata to the type (e.g. `since=N`)."""

    def _identity(cls):
        return cls

    return _identity
