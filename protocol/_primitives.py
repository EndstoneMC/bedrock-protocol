"""Protocol primitive types.

At Python runtime these are `Annotated[int, ...]` aliases; the bpc compiler
maps each name to a specific C++ in-memory type based on its on-the-wire
encoding.
"""

from typing import Annotated

type varint32 = Annotated[int, "varint32"]
type varint64 = Annotated[int, "varint64"]
type uvarint32 = Annotated[int, "uvarint32"]
type uvarint64 = Annotated[int, "uvarint64"]

type int8 = Annotated[int, "int8"]
type int16 = Annotated[int, "int16"]
type int32 = Annotated[int, "int32"]
type int64 = Annotated[int, "int64"]
type uint8 = Annotated[int, "uint8"]
type uint16 = Annotated[int, "uint16"]
type uint32 = Annotated[int, "uint32"]
type uint64 = Annotated[int, "uint64"]
