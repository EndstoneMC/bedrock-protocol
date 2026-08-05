"""`@type(cereal=False)` / `field(cereal=False)` — one BDS name, two wire shapes.

The version axis cannot express this: both encodings are live at the same
protocol version and the call site picks, so the two declarations tile no range
between them.
"""

from __future__ import annotations

import unittest

from harness import CompilerCase

PREAMBLE = """
from protocol import field, packet, type, uint32, uvarint32

package = "bedrock.protocol"
"""

TWO_SHAPES = (
    PREAMBLE
    + """

@type(cereal=False)
class Rule:
    value: uvarint32


class Rule:
    value: uint32
"""
)


class Declaration(CompilerCase):
    def test_the_pre_cereal_shape_lands_in_its_own_namespace(self) -> None:
        header, _ = self.compile(
            TWO_SHAPES
            + """

@packet(id=7)
class ThingPacket:
    cerealised: Rule
    hand_written: Rule = field(cereal=False)
"""
        )
        self.assertIn("struct Rule {\n    std::uint32_t value{};\n};", header)
        legacy = self.namespace(header, "legacy")
        self.assertIn("struct Rule {\n    std::uint32_t value{};\n};", legacy)
        self.assertIn("Rule cerealised{};", header)
        self.assertIn("legacy::Rule hand_written{};", header)

    def test_each_shape_gets_its_own_serializer(self) -> None:
        _, source = self.compile(
            TWO_SHAPES
            + """

@packet(id=7)
class ThingPacket:
    hand_written: Rule = field(cereal=False)
"""
        )
        self.assertIn("writeVarInt<std::uint32_t>(value.value)", self.body(source, "void Serializer<legacy::Rule>"))
        self.assertIn("write<std::uint32_t>(value.value)", self.body(source, "void Serializer<Rule>"))

    def test_the_flavour_reaches_a_list_element(self) -> None:
        header, _ = self.compile(
            TWO_SHAPES
            + """

@packet(id=7)
class ThingPacket:
    rules: list[Rule] = field(cereal=False)
"""
        )
        self.assertIn("std::vector<legacy::Rule> rules{};", header)

    def test_a_cerealised_type_may_reach_a_pre_cereal_one(self) -> None:
        """`field(cereal=False)` is written from a cerealised body, so references
        cross both ways and neither flavour can simply be emitted last. The
        pre-cereal definition has to precede the cerealised type that names it."""
        header, _ = self.compile(
            TWO_SHAPES
            + """

@type(until=2168)
class Settings:
    rules: list[Rule] = field(cereal=False)
"""
        )
        self.assertIn("std::vector<legacy::Rule> rules{};", header)
        self.assertLess(header.index("namespace legacy"), header.index("struct Settings"))

    def test_a_pre_cereal_type_may_reach_a_cerealised_one(self) -> None:
        """Lookup never goes the other way, so the cerealised definitions can
        always precede the pre-cereal block."""
        header, _ = self.compile(
            PREAMBLE
            + """

class Shared:
    n: uint32


@type(cereal=False)
class Rule:
    shared: Shared


class Rule:
    n: uint32


@packet(id=7)
class ThingPacket:
    rule: Rule = field(cereal=False)
"""
        )
        self.assertLess(header.index("struct Shared"), header.index("namespace legacy"))
        self.assertIn("Shared shared{};", self.namespace(header, "legacy"))


class Rejections(CompilerCase):
    def test_a_packet_takes_no_flavour(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7, cereal=False)
class ThingPacket:
    n: uint32
"""
        )
        self.assertIn("one wire shape per protocol version", message)

    def test_a_reference_to_a_flavour_that_is_not_declared_is_an_error(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

class Rule:
    value: uint32


@packet(id=7)
class ThingPacket:
    rule: Rule = field(cereal=False)
"""
        )
        self.assertIn("has no @type(cereal=False) declaration", message)

    def test_a_plain_reference_to_a_pre_cereal_only_type_is_an_error(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@type(cereal=False)
class Rule:
    value: uvarint32


@packet(id=7)
class ThingPacket:
    rule: Rule
"""
        )
        self.assertIn("declared only as @type(cereal=False)", message)

    def test_a_nested_type_takes_its_owner_flavour(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@packet(id=7)
class ThingPacket:
    @type(cereal=False)
    class Inner:
        n: uint32

    inner: Inner
"""
        )
        self.assertIn("a nested type takes its owner's flavour", message)


if __name__ == "__main__":
    unittest.main()
