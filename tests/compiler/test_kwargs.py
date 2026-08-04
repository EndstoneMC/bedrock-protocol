"""A DSL keyword the compiler does not read has to be an error.

Dropping one silently is the worst failure this compiler can have: the modeller
believes the wire changed and nothing did, and no golden can catch it.
"""

from __future__ import annotations

import unittest

from harness import CompilerCase

PREAMBLE = """
from enum import IntEnum

from protocol import field, packet, type, uint8, uint32, uvarint32, value, varint32

package = "bedrock.protocol"


class Kind(IntEnum, uint8):
    A = 0
    B = 1
"""


class FieldKwargs(CompilerCase):
    def test_a_misspelt_keyword_is_rejected(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    x: uvarint32 = field(prefixx=uint8)
"""
        )
        self.assertIn("field() has no 'prefixx' keyword", message)

    def test_tag_is_rejected_rather_than_ignored(self) -> None:
        """`tag=` is documented at length and never read: a union always takes
        the default uvarint32 index over declaration order. Spelling it must
        not quietly leave those bytes in place."""
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    payload: uvarint32 | varint32 = field(tag=Kind)
"""
        )
        self.assertIn("field(tag=...)", message)
        self.assertIn("not implemented", message)

    def test_a_positional_argument_is_rejected(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    x: uvarint32 = field(uint8)
"""
        )
        self.assertIn("field() takes keyword arguments only", message)

    def test_the_keywords_the_compiler_reads_still_pass(self) -> None:
        header, _ = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    n: uvarint32
    kind: Kind = field(type=uvarint32)
    xs: list[uint8] = field(prefix=uint8)
    ys: list[uint8] = field(count=lambda p: p.n)
    z: uvarint32 = field(since=1001, until=2168)
    big: uint32 = field(endian="big")
    gated: uvarint32 = field(when=lambda p: p.kind == Kind.A)
"""
        )
        self.assertIn("struct ThingPacket {", header)


class ValueKwargs(CompilerCase):
    def test_a_misspelt_keyword_is_rejected(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

class Other(IntEnum, uint8):
    A = value(0, sinse=1001)
"""
        )
        self.assertIn("value() has no 'sinse' keyword", message)

    def test_deprecated_is_rejected_rather_than_ignored(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

class Other(IntEnum, uint8):
    A = value(0, deprecated=1001)
"""
        )
        self.assertIn("value(deprecated=...)", message)
        self.assertIn("not implemented", message)


class GuardBlock(CompilerCase):
    def test_a_misspelt_guard_keyword_is_rejected(self) -> None:
        """An unrecognised keyword left the block unhoisted, and every field in
        it reached the wire ungated."""
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    n: uvarint32
    with field(whenn=lambda p: p.n == 1):
        a: uvarint32
"""
        )
        self.assertIn("guard block takes no 'whenn' keyword", message)

    def test_a_guard_block_needs_its_predicate(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    n: uvarint32
    with field():
        a: uvarint32
"""
        )
        self.assertIn("takes exactly field(when=<lambda>)", message)

    def test_a_guard_block_still_gates_its_fields(self) -> None:
        _, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    kind: Kind
    with field(when=lambda p: p.kind == Kind.A):
        a: uvarint32
        b: uvarint32
"""
        )
        write = self.body(source, "void Serializer<ThingPacket>::serialize")
        self.assertIn("if ((value.kind) == (Kind::A))", write)


class DecoratorKwargs(CompilerCase):
    def test_a_misspelt_packet_keyword_is_rejected(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7, form=1001)
class ThingPacket:
    x: uvarint32
"""
        )
        self.assertIn("packet() has no 'form' keyword", message)

    def test_deprecated_is_rejected_on_type(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@type(deprecated=1001)
class Thing:
    x: uvarint32
"""
        )
        self.assertIn("type(deprecated=...)", message)
        self.assertIn("not implemented", message)


if __name__ == "__main__":
    unittest.main()
