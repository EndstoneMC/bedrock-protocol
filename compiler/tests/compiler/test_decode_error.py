"""A failed read names the field it was reading through `stream.fail`."""

from __future__ import annotations

import unittest

from harness import CompilerCase

PREAMBLE = """
from protocol import array, field, int8, packet, uint8, uvarint32

package = "bedrock.protocol"
"""


class DecodeFailure(CompilerCase):
    def test_a_scalar_read_names_its_field(self) -> None:
        _, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    width: uvarint32
"""
        )
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertIn('if (!v) return stream.fail(v.error(), "width");', read)
        self.assertIn('return stream.fail(Errc::out_of_range, "width");', read)
        self.assertNotIn("std::unexpected", read)

    def test_a_list_element_names_its_field_and_index(self) -> None:
        _, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    cells: list[int8]
"""
        )
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertIn('if (!len0) return stream.fail(len0.error(), "cells");', read)
        self.assertIn('if (!v) return stream.fail(v.error(), "cells", i0);', read)

    def test_nested_containers_name_every_index(self) -> None:
        _, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    cells: list[array[uint8, 2]]
"""
        )
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertIn('if (!v) return stream.fail(v.error(), "cells", i0, i1);', read)

    def test_a_map_entry_names_its_field_and_index(self) -> None:
        _, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    tints: dict[uvarint32, uint8]
"""
        )
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertIn('if (!v) return stream.fail(v.error(), "tints", i0);', read)

    def test_a_union_names_its_field_when_the_discriminant_is_unknown(self) -> None:
        _, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    value: uint8 | int8
"""
        )
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertIn('return stream.fail(Errc::unknown_value, "value");', read)

    def test_a_struct_read_guards_no_depth(self) -> None:
        _, source = self.compile(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    width: uvarint32
"""
        )
        read = self.body(source, "auto Serializer<ThingPacket>::deserialize")
        self.assertNotIn("ReadScope", read)


if __name__ == "__main__":
    unittest.main()
