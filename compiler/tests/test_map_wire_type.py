"""`field(type=)` on a `dict[K, V]` — which half it reaches."""

from __future__ import annotations

import unittest

from harness import CompilerCase

PREAMBLE = """
from enum import IntEnum

from protocol import field, packet, uint8, uint32, uvarint32

package = "bedrock.protocol"


class Key(IntEnum, uint8):
    A = 0


class Other(IntEnum, uint8):
    B = 0


class Value:
    n: uint32
"""


class LoneTypeKeyword(CompilerCase):
    def test_it_reaches_the_key_and_the_struct_value_ignores_it(self) -> None:
        _, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    tints: dict[Key, Value] = field(type=str)
"""
        )
        write = self.body(source, "void Serializer<ThingPacket>::serialize")
        self.assertIn("Serializer<Key>::serialize(stream, k0)", write)
        self.assertIn("Serializer<Value>::serialize(stream, v0)", write)

    def test_both_halves_taking_it_is_an_error(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    tints: dict[Key, Other] = field(type=str)
"""
        )
        self.assertIn("reaches the key and the value alike", message)


class PerHalf(CompilerCase):
    def test_each_half_is_spelled(self) -> None:
        _, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    tints: dict[Key, Other] = field(type=dict[str, uint8])
"""
        )
        write = self.body(source, "void Serializer<ThingPacket>::serialize")
        self.assertIn("Serializer<Key>::serialize(stream, k0)", write)
        self.assertIn("stream.write<std::uint8_t>(v0)", write)

    def test_each_half_takes_its_own_wire_type(self) -> None:
        _, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    tints: dict[Key, Other] = field(type=dict[uvarint32, str])
"""
        )
        write = self.body(source, "void Serializer<ThingPacket>::serialize")
        self.assertIn("stream.writeVarInt<std::uint32_t>(k0)", write)
        self.assertIn("Serializer<Other>::serialize(stream, v0)", write)

    def test_it_needs_a_dict_field(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    n: Key = field(type=dict[str, uint8])
"""
        )
        self.assertIn("and this one is not one", message)


if __name__ == "__main__":
    unittest.main()
