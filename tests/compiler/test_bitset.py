"""`bitset[N]` — a fixed-width `std::bitset<N>` in the base-128 wire form."""

from __future__ import annotations

import unittest

from harness import CompilerCase

PREAMBLE = """
from protocol import bitset, field, packet, uvarint32

package = "bedrock.protocol"
"""

#: A packet whose bitset width is named by a member of its own nested enum.
#: `members` are further enum members, `width` the subscript under test.
COUNTED = """
from enum import IntEnum, auto

from protocol import bitset, field, packet, uint32, value

package = "bedrock.protocol"


@packet(id=7)
class ThingPacket:
    class Flag(IntEnum, uint32):
        LOW = 0
        HIGH = 1
{members}
        FLAG_NUM = auto()

    flags: bitset[{width}]
"""


class Bitset(CompilerCase):
    def test_a_bitset_field_is_a_std_bitset(self) -> None:
        header, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    input_data: bitset[65]
"""
        )
        self.assertIn("std::bitset<65> input_data{};", header)
        self.assertIn("#include <bitset>", header)

        write = self.body(source, "void Serializer<ThingPacket>::serialize")
        self.assertIn("Serializer<std::bitset<65>>::serialize(stream, value.input_data);", write)
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertIn("Serializer<std::bitset<65>>::deserialize(stream);", read)
        self.assertIn("#include <bedrock/bitset.hpp>", source)

    def test_a_width_over_64_is_kept_verbatim(self) -> None:
        """The codec must never stage the value in an integer: bit 64 of
        PlayerAuthInput's input data is a real flag."""
        header, _ = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    flags: bitset[130]
"""
        )
        self.assertIn("std::bitset<130> flags{};", header)
        self.assertNotIn("std::uint64_t flags", header)

    def test_a_bitset_nests_in_a_list(self) -> None:
        header, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    rows: list[bitset[12]]
"""
        )
        self.assertIn("std::vector<std::bitset<12>> rows{};", header)
        write = self.body(source, "void Serializer<ThingPacket>::serialize")
        self.assertIn("Serializer<std::bitset<12>>::serialize(stream, e0);", write)

    def test_a_field_gates_on_one_bit(self) -> None:
        """BDS packs a run of flags into a bitset and gates later fields on
        individual bits, so a predicate has to reach a bit rather than compare
        a whole value. Bit 64 is the one a `uint64_t` would lose."""
        _, source = self.compile(
            """
from enum import IntEnum

from protocol import bitset, field, packet, uint32, uvarint32

package = "bedrock.protocol"


@packet(id=7)
class ThingPacket:
    class Flag(IntEnum, uint32):
        MIDDLE = 34
        TOP = 64

    flags: bitset[65]
    gated: uvarint32 = field(when=lambda p: p.flags.test(ThingPacket.Flag.MIDDLE))
    with field(when=lambda p: p.flags.test(64)):
        also_gated: uvarint32
"""
        )
        write = self.body(source, "void Serializer<ThingPacket>::serialize")
        self.assertIn(
            "if (value.flags.test(static_cast<std::size_t>(ThingPacket::Flag::MIDDLE)))",
            write,
        )
        self.assertIn("if (value.flags.test(static_cast<std::size_t>(64)))", write)
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertIn("if (out.flags.test(static_cast<std::size_t>(64)))", read)
        self.assertIn("#include <cstddef>", source)

    def test_a_bit_test_needs_a_bitset(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    flags: uvarint32
    gated: uvarint32 = field(when=lambda p: p.flags.test(3))
"""
        )
        self.assertIn(".test(...) applies to an earlier bitset[N] field", message)

    def test_a_bit_test_needs_an_earlier_field(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    gated: uvarint32 = field(when=lambda p: p.flags.test(3))
    flags: bitset[65]
"""
        )
        self.assertIn("is not a field declared before it", message)

    def test_an_unknown_call_is_rejected(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    flags: bitset[65]
    gated: uvarint32 = field(when=lambda p: p.flags.count() > 0)
"""
        )
        self.assertIn("calls only len(<field>) or <field>.test(<bit>)", message)

    def test_a_width_names_a_nested_enum_member(self) -> None:
        """BDS sizes PlayerAuthInput's bitset by its own `INPUT_NUM` sentinel
        rather than repeating the number."""
        header, _ = self.compile(COUNTED.format(members="", width="Flag.FLAG_NUM"))
        self.assertIn("std::bitset<2> flags{};", header)

    def test_the_width_follows_the_member_per_snapshot(self) -> None:
        header, _ = self.compile(
            COUNTED.format(members="        EXTRA = value(2, since=2168)", width="Flag.FLAG_NUM")
        )
        self.assertIn("std::bitset<2> flags{};", self.namespace(header, "base"))
        self.assertIn("std::bitset<3> flags{};", self.namespace(header, "v2168"))

    def test_an_unknown_member_is_rejected(self) -> None:
        message = self.rejects(COUNTED.format(members="", width="Flag.MISSING"))
        self.assertIn("bitset[...] needs a positive integer width", message)

    def test_a_non_literal_width_is_rejected(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    n: uvarint32
    flags: bitset[n]
"""
        )
        self.assertIn("bitset[...] needs a positive integer width", message)

    def test_a_zero_width_is_rejected(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    flags: bitset[0]
"""
        )
        self.assertIn("bitset[...] needs a positive integer width", message)


if __name__ == "__main__":
    unittest.main()
