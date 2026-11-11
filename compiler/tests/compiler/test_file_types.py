"""`<module>_types<V>` -- every type a module declares, per version.

A binding walks one version whole rather than naming types, so the list has to
hold exactly the C++ types that version reaches: a gated type is absent outside
its range, a nested type follows its owner, and the pre-cereal tree is kept
apart because it may repeat a name the cerealised tree also uses.
"""

from __future__ import annotations

import unittest

from harness import CompilerCase

SOURCE = """
from enum import IntEnum

from protocol import field, packet, type, uint8, uvarint32

package = "bedrock.protocol"


class Kind(IntEnum, uint8):
    A = 0
    B = 1


@type(cereal=False)
class Rule:
    value: uvarint32


class Rule:
    value: uvarint32


@packet(id=7)
class ThingPacket:
    class Entry:
        n: uvarint32

    @type(until=944)
    class Gone:
        n: uvarint32

    kind: Kind
    entries: list[Entry]
    rule: Rule = field(cereal=False)
    tail: uvarint32 = field(since=944)
"""


class FileTypes(CompilerCase):
    def setUp(self) -> None:
        self.header, _ = self.compile(SOURCE, module="things")

    def selector(self, clause: str) -> str:
        start = self.header.index(f"template <int V> requires ({clause})\nstruct things_types<V> {{")
        return self.header[start : self.header.index("};", start)]

    def test_each_range_lists_the_types_it_reaches(self) -> None:
        before = self.selector("V < 944")
        self.assertIn("Kind,\n        Rule,\n        base::ThingPacket,", before)
        self.assertIn("base::ThingPacket::Entry,", before)
        self.assertIn("base::ThingPacket::Gone>;", before)
        after = self.selector("V >= 944")
        self.assertIn("v944::ThingPacket,\n        v944::ThingPacket::Entry>;", after)

    def test_a_gated_nested_type_is_absent_outside_its_range(self) -> None:
        self.assertNotIn("Gone", self.selector("V >= 944"))

    def test_the_pre_cereal_tree_has_its_own_list(self) -> None:
        for clause in ("V < 944", "V >= 944"):
            self.assertIn("using legacy = type_list<\n        legacy::Rule>;", self.selector(clause))

    def test_a_module_with_one_shape_defines_the_primary(self) -> None:
        header, _ = self.compile(
            """
from protocol import uvarint32

package = "bedrock.protocol"


class Plain:
    n: uvarint32
""",
            module="plain",
        )
        self.assertIn(
            "template <int V>\nstruct plain_types {\n    using cereal = type_list<\n        Plain>;\n"
            "    using legacy = type_list<>;\n};",
            header,
        )


class Reflection(CompilerCase):
    def test_an_enum_carries_its_schema_names(self) -> None:
        header, _ = self.compile(
            """
from enum import IntEnum

from protocol import uint8

package = "bedrock.protocol"


class Color(IntEnum, uint8):
    REBECCA_PURPLE = 0
    WHITE = 1
"""
        )
        self.assertIn(
            'schema_names_v<Color>{{\n    "REBECCA_PURPLE",\n    "WHITE",\n}};',
            header,
        )
        self.assertIn('names_v<Color>{{\n    "rebeccapurple",\n    "white",\n}};', header)

    def test_a_struct_compares_member_wise(self) -> None:
        header, _ = self.compile(
            """
from protocol import uvarint32

package = "bedrock.protocol"


class Pair:
    a: uvarint32
    b: uvarint32
"""
        )
        self.assertIn("friend bool operator==(const Pair &, const Pair &) = default;", header)

    def test_a_primitive_alias_names_its_primitive(self) -> None:
        header, _ = self.compile(
            """
from protocol import uint32

package = "bedrock.protocol"

type BlockRuntimeId = uint32
"""
        )
        self.assertIn("struct primitive_alias<BlockRuntimeId> { using type = std::uint32_t; };", header)


if __name__ == "__main__":
    unittest.main()
