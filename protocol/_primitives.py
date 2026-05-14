"""Protocol primitive types.

At Python runtime these are aliases for `int`; the bpc compiler maps each name
to a specific C++ in-memory type based on its on-the-wire encoding.
"""

varint32 = int
varint64 = int
uvarint32 = int
uvarint64 = int
