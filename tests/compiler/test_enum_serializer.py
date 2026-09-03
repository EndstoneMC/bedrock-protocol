"""A name-coded enum's `Serializer` follows the enum's own versioning.

A name-coded enum is the one kind that gets a `Serializer` specialization of its
own at namespace scope. When the enum is versioned it is a distinct C++ type per
fresh snapshot, so it needs one specialization per type under the snapshot-
qualified name -- exactly as a versioned struct does, and as the reflection
tables already did.
"""

from __future__ import annotations

import unittest

from harness import CompilerCase

PREAMBLE = """
from enum import IntEnum

from protocol import field, packet, type, uint8

package = "bedrock.protocol"
"""

GATED_ENUM = (
    PREAMBLE
    + """

@type(since=2168)
class ScorePacketEntryAction(IntEnum, uint8):
    REMOVE = 0
    CHANGE_PLAYER = 1


@type(since=2168)
class RemoveScore:
    action: ScorePacketEntryAction = field(type=str)


@packet(id=108, since=2168)
class SetScorePacket:
    entry: RemoveScore
"""
)


class VersionedNameCodedEnum(CompilerCase):
    def test_the_specialization_is_snapshot_qualified(self) -> None:
        header, source = self.compile(GATED_ENUM)
        self.assertIn("struct Serializer<v2168::ScorePacketEntryAction> {", header)
        self.assertNotIn("struct Serializer<ScorePacketEntryAction> {", header)
        self.assertIn("void Serializer<v2168::ScorePacketEntryAction>::serialize", source)
        self.assertNotIn("void Serializer<ScorePacketEntryAction>::serialize", source)

    def test_a_user_calls_the_specialization_that_exists(self) -> None:
        """The struct body spells the enum snapshot-qualified, so the
        declaration it resolves to has to carry the same spelling or the call
        implicitly instantiates the undefined primary."""
        _, source = self.compile(GATED_ENUM)
        called = "Serializer<v2168::ScorePacketEntryAction>::serialize(stream, value.action);"
        self.assertIn(called, source)
        self.assertIn("void Serializer<v2168::ScorePacketEntryAction>::serialize", source)

    def test_a_renumbered_enum_gets_one_specialization_per_shape(self) -> None:
        header, source = self.compile(
            PREAMBLE
            + """

@type(until=2168)
class Kind(IntEnum, uint8):
    ALPHA = 0


@type(since=2168)
class Kind(IntEnum, uint8):
    ALPHA = 0
    BETA = 1


@packet(id=7)
class ThingPacket:
    kind: Kind = field(type=str)
"""
        )
        self.assertIn("struct Serializer<base::Kind> {", header)
        self.assertIn("struct Serializer<v2168::Kind> {", header)
        # each shape carries its own members, in the reflected table the write
        # reads and in the read's own keyed one
        new = header.index("names_v<v2168::Kind>")
        self.assertIn('"beta",', header[new : header.index("}};", new)])
        old = header.index("names_v<base::Kind>")
        self.assertNotIn('"beta",', header[old : header.index("}};", old)])
        self.assertIn(
            "enum_cast<v2168::Kind>(*v)", self.body(source, "auto Serializer<v2168::Kind>::deserialize")
        )
        self.assertIn(
            "enum_cast<base::Kind>(*v)", self.body(source, "auto Serializer<base::Kind>::deserialize")
        )

    def test_a_gated_field_still_reaches_its_enum(self) -> None:
        """A `when=` gate wraps the field's type, and the walk collecting
        name-coded enums used to stop at it: the body called a `Serializer`
        specialization the header never declared."""
        header, source = self.compile(
            PREAMBLE
            + """

class Kind(IntEnum, uint8):
    A = 0
    B = 1


@packet(id=7)
class ThingPacket:
    flag: bool
    kind: Kind = field(type=str, when=lambda p: p.flag)
"""
        )
        self.assertIn("struct Serializer<Kind> {", header)
        self.assertIn("void Serializer<Kind>::serialize", source)

    def test_an_unversioned_enum_is_unqualified(self) -> None:
        header, source = self.compile(
            PREAMBLE
            + """

class Kind(IntEnum, uint8):
    ALPHA = 0


@packet(id=7)
class ThingPacket:
    kind: Kind = field(type=str)
"""
        )
        self.assertIn("struct Serializer<Kind> {", header)
        self.assertIn("void Serializer<Kind>::serialize", source)
        self.assertNotIn("v2168::Kind", source)


class ReadIsAKeyedLookup(CompilerCase):
    """The read defers to `enum_cast`, which keys a table per enum on first use.

    `enum_count` / `enum_names` / `enum_values` are the reflection API
    downstream projects consume; a codec must not be built on them. A scan over
    them is also linear, with a case-insensitive compare per candidate, and
    `LevelSoundEvent` runs to 600+ members on a hot path. The table used to be
    emitted inline in each deserialize; it now lives behind `enum_cast` in
    `enum.hpp`, so what the generated read must show is that it goes there and
    keys the snapshot's own enum.
    """

    SCHEMA = """
from enum import IntEnum

from protocol import field, packet, uint8, value

package = "bedrock.protocol"


class Kind(IntEnum, uint8):
    ALPHA = 0
    BRAVO = 1


@packet(id=7)
class ThingPacket:
    kind: Kind = field(type=str)
"""

    def read(self, source: str) -> str:
        return self.body(source, "auto Serializer<Kind>::deserialize")

    def test_the_read_defers_to_enum_cast(self) -> None:
        _, source = self.compile(self.SCHEMA)
        read = self.read(source)
        self.assertIn("auto v = stream.read<std::string>();", read)
        self.assertIn("enum_cast<Kind>(*v)", read)

    def test_the_read_names_no_reflection_helper(self) -> None:
        _, source = self.compile(self.SCHEMA)
        read = self.read(source)
        for helper in ("enum_count", "enum_names", "enum_values", "std::equal"):
            self.assertNotIn(helper, read)

    def test_the_write_still_uses_enum_name(self) -> None:
        """Reflection in the write is fine and stays: one lookup, no scan."""
        _, source = self.compile(self.SCHEMA)
        write = self.body(source, "void Serializer<Kind>::serialize")
        self.assertIn("enum_name(value)", write)

    def test_the_map_carries_the_snapshots_members_only(self) -> None:
        header, source = self.compile(
            """
from enum import IntEnum

from protocol import field, packet, uint8, value

package = "bedrock.protocol"


class Kind(IntEnum, uint8):
    ALPHA = 0
    BRAVO = value(1, since=2168)


@packet(id=7)
class ThingPacket:
    kind: Kind = field(type=str)
"""
        )
        base = self.body(source, "auto Serializer<base::Kind>::deserialize")
        later = self.body(source, "auto Serializer<v2168::Kind>::deserialize")
        # each read casts its own snapshot's enum, and that enum's table is what
        # decides which members resolve
        self.assertIn("enum_cast<base::Kind>(*v)", base)
        self.assertIn("enum_cast<v2168::Kind>(*v)", later)
        new = header.index("names_v<v2168::Kind>")
        self.assertIn('"bravo",', header[new : header.index("}};", new)])
        old = header.index("names_v<base::Kind>")
        self.assertNotIn('"bravo",', header[old : header.index("}};", old)])

    def test_a_versioned_read_keys_the_qualified_enum(self) -> None:
        _, source = self.compile(GATED_ENUM)
        read = self.body(source, "auto Serializer<v2168::ScorePacketEntryAction>::deserialize")
        self.assertIn("enum_cast<v2168::ScorePacketEntryAction>(*v)", read)

    def test_members_sharing_a_folded_wire_name_are_rejected(self) -> None:
        """The map would keep one of them and say nothing."""
        message = self.rejects(
            """
from enum import Enum

from protocol import field, packet, uint8

package = "bedrock.protocol"


class Kind(Enum, uint8):
    ALPHA = 0, "Alpha"
    ALPHA_TOO = 1, "ALPHA"


@packet(id=7)
class ThingPacket:
    kind: Kind = field(type=str)
"""
        )
        self.assertIn("share a wire name once folded", message)
        self.assertIn("ALPHA, ALPHA_TOO", message)


if __name__ == "__main__":
    unittest.main()
