"""`field(count=)` — a list whose length is not on the wire."""

from __future__ import annotations

import unittest

from harness import CompilerCase

PREAMBLE = """
from typing import Literal

from protocol import field, int8, packet, uvarint32

package = "bedrock.protocol"
"""


class CountedList(CompilerCase):
    def test_counted_list_carries_no_prefix(self) -> None:
        header, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    cells: list[int8] = field(count=lambda p: 256)
"""
        )
        self.assertIn("std::vector<std::int8_t> cells{};", header)
        write = self.body(source, "void Serializer<ThingPacket>::serialize")
        self.assertNotIn("writeVarInt<std::uint32_t>(value.cells.size())", write)
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertIn("for (auto rep0 = 256; rep0 > 0; --rep0)", read)

    def test_counted_list_may_be_optional(self) -> None:
        """A cerealised optional list still has its length written elsewhere:
        the presence flag and the count are orthogonal."""
        header, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    _true_1: Literal[True]
    cells: list[int8] | None = field(count=lambda p: 256)
"""
        )
        self.assertIn("std::optional<std::vector<std::int8_t>> cells{};", header)
        self.assertIn("#include <optional>", header)

        write = self.body(source, "void Serializer<ThingPacket>::serialize")
        self.assertIn("stream.write<bool>(value.cells.has_value());", write)
        self.assertNotIn("(*value.cells).size()", write)
        self.assertIn("for (const auto &e0 : (*value.cells))", write)

        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertIn("std::vector<std::int8_t> staged{};", read)
        self.assertIn("for (auto rep0 = 256; rep0 > 0; --rep0)", read)
        self.assertNotIn("stream.readVarInt<std::uint32_t>()", read)

    def test_an_optional_count_reads_the_struct_not_the_staging_temporary(self) -> None:
        """The count is an expression over the *struct's* earlier fields. An
        optional stages its payload in a local before moving it in, so a count
        resolved against the target would read the temporary instead."""
        _, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    width: uvarint32
    height: uvarint32
    cells: list[int8] | None = field(count=lambda p: p.width * p.height)
"""
        )
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertIn("for (auto rep0 = (out.width) * (out.height); rep0 > 0; --rep0)", read)
        self.assertNotIn("staged.width", read)

    def test_count_may_read_an_earlier_lists_length(self) -> None:
        """BDS writes several parallel runs behind one count: the second run's
        length is the first run's, and nothing on the wire repeats it."""
        _, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    entries: list[uvarint32]
    flags: list[int8] = field(count=lambda p: len(p.entries))
"""
        )
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertIn("for (auto rep0 = out.entries.size(); rep0 > 0; --rep0)", read)

    def test_len_needs_a_sized_field(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    n: uvarint32
    cells: list[int8] = field(count=lambda p: len(p.n))
"""
        )
        self.assertIn("len(...) applies to an earlier list, map or string field", message)

    def test_count_still_needs_a_list(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    cells: uvarint32 | None = field(count=lambda p: 256)
"""
        )
        self.assertIn("field(count=...) applies to a list[T] field", message)

    def test_count_and_prefix_stay_mutually_exclusive(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    cells: list[int8] | None = field(count=lambda p: 256, prefix=uvarint32)
"""
        )
        self.assertIn("mutually exclusive", message)


if __name__ == "__main__":
    unittest.main()
