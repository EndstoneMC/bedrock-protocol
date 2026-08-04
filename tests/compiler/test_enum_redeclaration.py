"""An enum whose members were renumbered is redeclared, like a reshaped struct.

`value(since=)` / `value(until=)` covers a member arriving or going, but it
cannot give one member two different values, and it cannot express a wholesale
renumbering. BDS's `Memory::MemoryCategory` did exactly that at 2168: one member
removed, twenty added, and most survivors shifted by one of six amounts.
"""

from __future__ import annotations

import unittest

from harness import CompilerCase

PREAMBLE = """
from enum import IntEnum, auto

from protocol import field, packet, type, uint8, value

package = "bedrock.protocol"
"""

RENUMBERED = (
    PREAMBLE
    + """

@type(until=2168)
class MemoryCategory(IntEnum, uint8):
    UNKNOWN = 0
    PERSONA = 54
    RENDERING = 55
    COUNT = auto()


@type(since=2168)
class MemoryCategory(IntEnum, uint8):
    UNKNOWN = 0
    RENDERING = 62
    SCRIPTING = 63
    COUNT = auto()


@packet(id=315)
class ThingPacket:
    category: MemoryCategory
"""
)


class RedeclaredEnum(CompilerCase):
    def test_each_range_gets_its_own_numbering(self) -> None:
        header, _ = self.compile(RENUMBERED)
        base = self.namespace(header, "base")
        later = self.namespace(header, "v2168")

        self.assertIn("PERSONA = 54,", base)
        self.assertIn("RENDERING = 55,", base)
        self.assertNotIn("SCRIPTING", base)

        self.assertNotIn("PERSONA", later)
        self.assertIn("RENDERING = 62,", later)
        self.assertIn("SCRIPTING = 63,", later)

    def test_the_count_sentinel_follows_its_own_range(self) -> None:
        header, _ = self.compile(RENUMBERED)
        self.assertIn("COUNT = 56,", header)
        self.assertIn("COUNT = 64,", header)

    def test_the_selector_dispatches_on_the_version(self) -> None:
        header, _ = self.compile(RENUMBERED)
        self.assertIn("struct MemoryCategory_<V> { using type = base::MemoryCategory; };", header)
        self.assertIn("struct MemoryCategory_<V> { using type = v2168::MemoryCategory; };", header)
        self.assertIn("using MemoryCategory = MemoryCategory_<2168>;", header)

    def test_a_user_of_the_enum_is_versioned_with_it(self) -> None:
        _, source = self.compile(RENUMBERED)
        self.assertIn("void Serializer<base::ThingPacket>::serialize", source)
        self.assertIn("void Serializer<v2168::ThingPacket>::serialize", source)

    def test_value_gating_still_works_inside_one_declaration(self) -> None:
        header, _ = self.compile(
            PREAMBLE
            + """

class Kind(IntEnum, uint8):
    A = 0
    B = value(1, since=1001)
"""
        )
        self.assertNotIn("B = 1,", header[: header.index("namespace v1001 {")])
        self.assertIn("B = 1,", header[header.index("namespace v1001 {") :])

    def test_redeclarations_must_tile_one_range(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@type(until=1001)
class Kind(IntEnum, uint8):
    A = 0


@type(since=2168)
class Kind(IntEnum, uint8):
    A = 1
"""
        )
        self.assertIn("redeclarations must be adjacent", message)

    def test_only_the_last_declaration_may_be_open(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@type(since=975)
class Kind(IntEnum, uint8):
    A = 0


@type(since=2168)
class Kind(IntEnum, uint8):
    A = 1
"""
        )
        self.assertIn("only the last declaration may omit until=", message)

    def test_the_underlying_type_may_not_change(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

@type(until=2168)
class Kind(IntEnum, uint8):
    A = 0


@type(since=2168)
class Kind(IntEnum, int):
    A = 1
"""
        )
        self.assertIn("one underlying type", message)

    def test_a_repeated_nested_enum_still_collapses(self) -> None:
        """A redeclared owner has to repeat each nested type verbatim in every
        body; identical repeats are one C++ type, not a redeclaration."""
        header, _ = self.compile(
            PREAMBLE
            + """

@packet(id=7, until=2168)
class ThingPacket:
    class Kind(IntEnum, uint8):
        A = 0

    kind: Kind
    extra: uint8


@packet(id=7, since=2168)
class ThingPacket:
    class Kind(IntEnum, uint8):
        A = 0

    kind: Kind
"""
        )
        self.assertIn("using Kind = base::ThingPacket::Kind;", header)

    def test_disagreeing_nested_bodies_inherit_the_owner_range(self) -> None:
        """The bodies carry no range of their own -- the owner declaration each
        was written in says which snapshot it belongs to."""
        header, _ = self.compile(
            PREAMBLE
            + """

@packet(id=7, until=2168)
class ThingPacket:
    class Kind(IntEnum, uint8):
        A = 0

    kind: Kind


@packet(id=7, since=2168)
class ThingPacket:
    class Kind(IntEnum, uint8):
        A = 0
        B = 1

    kind: Kind
"""
        )
        self.assertNotIn("B = 1,", self.namespace(header, "base"))
        self.assertIn("B = 1,", self.namespace(header, "v2168"))

    def test_a_nested_body_may_write_its_own_range(self) -> None:
        """An explicit `@type(...)` on the nested class wins over the owner's,
        for a nested type whose reshape lands somewhere else."""
        header, _ = self.compile(
            PREAMBLE
            + """

@packet(id=7, until=2168)
class ThingPacket:
    @type(until=1001)
    class Kind(IntEnum, uint8):
        A = 0

    kind: Kind


@packet(id=7, since=2168)
class ThingPacket:
    @type(since=1001)
    class Kind(IntEnum, uint8):
        A = 0
        B = 1

    kind: Kind
"""
        )
        self.assertNotIn("B = 1,", self.namespace(header, "base"))
        self.assertIn("B = 1,", self.namespace(header, "v1001"))


if __name__ == "__main__":
    unittest.main()
