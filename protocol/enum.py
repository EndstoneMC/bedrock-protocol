"""DSL helpers consumed by the bpc compiler.

griffe reads these statically; at runtime they're intentional no-ops.
"""


def value(v, since=None):
    """Mark a member's wire value, optionally gated by protocol version."""
    return v
