"""Protocol primitive types.

At Python runtime these are `Annotated[int, ...]` aliases; the bpc compiler
maps each name to a specific C++ in-memory type based on its on-the-wire
encoding.
"""

from typing import Annotated

varint32 = Annotated[int, "varint32"]
varint64 = Annotated[int, "varint64"]
uvarint32 = Annotated[int, "uvarint32"]
uvarint64 = Annotated[int, "uvarint64"]
