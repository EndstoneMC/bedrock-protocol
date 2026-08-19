"""`array[T, N]` — a fixed-length run whose size lives in the type."""

from __future__ import annotations

import unittest

from harness import CompilerCase

PREAMBLE = """
from enum import IntEnum
from typing import Literal

from protocol import array, field, int8, packet, type, uint8, uvarint32

package = "bedrock.protocol"
"""


class FixedArray(CompilerCase):
    def test_an_array_spells_std_array_and_writes_no_length(self) -> None:
        header, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    cells: array[int8, 256]
"""
        )
        self.assertIn("std::array<std::int8_t, 256> cells{};", header)
        self.assertIn("#include <array>", header)

        write = self.body(source, "void Serializer<ThingPacket>::serialize")
        self.assertNotIn("size()", write)
        self.assertIn("for (const auto &e0 : value.cells)", write)

        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertNotIn("readVarInt<std::uint32_t>", read)
        self.assertIn("for (std::size_t i0 = 0; i0 < 256; ++i0)", read)
        self.assertIn("out.cells[i0]", read)

    def test_the_read_indexes_rather_than_appending(self) -> None:
        """A `std::array` is already its full size: `.clear()` / `.emplace_back()`
        are what a `std::vector` read reaches for and it has neither."""
        _, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    cells: array[int8, 4]
"""
        )
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertNotIn("clear()", read)
        self.assertNotIn("emplace_back()", read)

    def test_arrays_nest(self) -> None:
        header, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    rows: array[array[int8, 16], 16]
"""
        )
        self.assertIn("std::array<std::array<std::int8_t, 16>, 16> rows{};", header)
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertIn("for (std::size_t i0 = 0; i0 < 16; ++i0)", read)
        self.assertIn("for (std::size_t i1 = 0; i1 < 16; ++i1)", read)
        self.assertIn("out.rows[i0][i1]", read)

    def test_an_array_may_be_optional(self) -> None:
        header, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    _true_1: Literal[True]
    cells: array[int8, 256] | None
"""
        )
        self.assertIn("std::optional<std::array<std::int8_t, 256>> cells{};", header)
        write = self.body(source, "void Serializer<ThingPacket>::serialize")
        self.assertIn("stream.write<bool>(value.cells.has_value());", write)
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertIn("std::array<std::int8_t, 256> staged{};", read)
        self.assertIn("staged[i0]", read)

    def test_a_struct_element_routes_through_its_serializer(self) -> None:
        _, source = self.compile(
            PREAMBLE
            + """

class Slot:
    id: uvarint32


@packet(id=7)
class ThingPacket:
    slots: array[Slot, 9]
"""
        )
        write = self.body(source, "void Serializer<ThingPacket>::serialize")
        self.assertIn("Serializer<Slot>::serialize(stream, e0);", write)
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertIn("out.slots[i0] = *v;", read)

    def test_a_list_of_arrays_keeps_the_lists_prefix(self) -> None:
        """The prefix belongs to the `list[T]` alone: the array inside it still
        has nothing on the wire marking its length."""
        header, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    rows: list[array[int8, 16]]
"""
        )
        self.assertIn("std::vector<std::array<std::int8_t, 16>> rows{};", header)
        write = self.body(source, "void Serializer<ThingPacket>::serialize")
        self.assertIn("stream.writeVarInt<std::uint32_t>(value.rows.size());", write)
        self.assertEqual(write.count("writeVarInt<std::uint32_t>"), 1)

    def test_a_size_may_name_a_nested_enum_member(self) -> None:
        """As a `bitset[Enum.MEMBER]` width does — BDS sizes an array by its own
        count sentinel, which moves as members are added."""
        header, _ = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    class Slot(IntEnum, uint8):
        HEAD = 0
        CHEST = 1
        COUNT = 2

    slots: array[uvarint32, Slot.COUNT]
"""
        )
        self.assertIn("std::array<std::uint32_t, 2> slots{};", header)

    def test_a_size_sentinel_follows_the_enum_across_snapshots(self) -> None:
        header, _ = self.compile(
            """
from enum import IntEnum, auto

from protocol import array, packet, uint8, uvarint32, value

package = "bedrock.protocol"


@packet(id=7)
class ThingPacket:
    class Slot(IntEnum, uint8):
        HEAD = 0
        CHEST = 1
        LEGS = value(2, since=1001)
        COUNT = auto()

    slots: array[uvarint32, Slot.COUNT]
"""
        )
        self.assertIn("std::array<std::uint32_t, 2> slots{};", self.namespace(header, "base"))
        self.assertIn("std::array<std::uint32_t, 3> slots{};", self.namespace(header, "v1001"))

    def test_a_size_must_be_a_positive_integer(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    cells: array[int8, 0]
"""
        )
        self.assertIn("array[...] needs a positive integer size", message)

    def test_an_array_takes_exactly_an_element_type_and_a_size(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    cells: array[int8]
"""
        )
        self.assertIn("array[...] needs exactly an element type and a size", message)

    def test_count_is_rejected_on_an_array(self) -> None:
        """The size is in the type; a second one in a lambda could disagree."""
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    cells: array[int8, 256] = field(count=lambda p: 256)
"""
        )
        self.assertIn("already carries its size in its type", message)


if __name__ == "__main__":
    unittest.main()
