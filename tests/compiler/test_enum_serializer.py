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
        self.assertIn('{E::BETA, "BETA"}', self.body(source, "void Serializer<v2168::Kind>::serialize"))
        self.assertNotIn("BETA", self.body(source, "void Serializer<base::Kind>::serialize"))

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


if __name__ == "__main__":
    unittest.main()
