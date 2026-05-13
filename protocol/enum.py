"""DSL helpers consumed by the bpc compiler.

griffe reads these statically; at runtime they're intentional no-ops.
"""


def value(v, since=None):
    """Mark a member's wire value, optionally gated by protocol version."""
    return v


def enum(*, since=None):
    """Class decorator: attach metadata to the type (e.g. `since=N`)."""

    def _identity(cls):
        return cls

    return _identity
