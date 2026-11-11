"""A nested type whose own nested types come with it into a fresh snapshot.

A later snapshot defines a nested type afresh only where that type moved, and
aliases the rest. But defining one afresh redefines its whole subtree: a
grandchild of the versioned owner is a distinct C++ type in the new namespace
even though its own shape never changed. Emitting a serializer only for the
types that moved leaves that grandchild declared and unserializable, and the
parent's own serializer then fails to compile on a call into it.
"""

from __future__ import annotations

import unittest

from harness import CompilerCase

#: `Outer.Middle` gains a field at 944, so v944 defines it afresh -- and with
#: it `Middle.Leaf`, whose shape never moved.
SOURCE = """
from protocol import field, packet, type, uvarint32

package = "bedrock.protocol"


class Outer:
    class Middle:
        class Leaf:
            n: uvarint32

        leaves: list[Leaf]
        tail: uvarint32 = field(since=944)


@packet(id=7)
class CarrierPacket:
    middle: Outer.Middle
"""


class VersionedNestedSubtree(CompilerCase):
    def test_the_grandchild_is_redefined_in_the_new_snapshot(self) -> None:
        header, _ = self.compile(SOURCE)
        self.assertIn("struct Leaf", self.namespace(header, "v944"))

    def test_the_grandchild_gets_its_own_serializer(self) -> None:
        """The bug: only types that moved were emitted for a later snapshot, so
        the grandchild had a declaration and no `Serializer` specialization."""
        _, source = self.compile(SOURCE)
        self.assertIn("Serializer<v944::Outer::Middle::Leaf>::serialize", source)
        self.assertIn("Serializer<base::Outer::Middle::Leaf>::serialize", source)

    def test_the_parent_calls_into_its_own_snapshot(self) -> None:
        _, source = self.compile(SOURCE)
        body = self.body(source, "void Serializer<v944::Outer::Middle>::serialize")
        self.assertIn("Serializer<v944::Outer::Middle::Leaf>::serialize", body)
        self.assertNotIn("Serializer<base::Outer::Middle::Leaf>::serialize", body)

    def test_an_unmoved_sibling_subtree_still_aliases(self) -> None:
        """Only the versioned branch is redefined -- a sibling that did not move
        stays one C++ type, so nothing emits a second serializer for it."""
        _, source = self.compile(
            """
from protocol import field, packet, type, uvarint32

package = "bedrock.protocol"


class Outer:
    class Steady:
        class Leaf:
            n: uvarint32

        leaves: list[Leaf]

    class Middle:
        tail: uvarint32 = field(since=944)


@packet(id=7)
class CarrierPacket:
    steady: Outer.Steady
    middle: Outer.Middle
"""
        )
        self.assertEqual(source.count("void Serializer<base::Outer::Steady::Leaf>::serialize"), 1)
        self.assertNotIn("v944::Outer::Steady::Leaf", source)


if __name__ == "__main__":
    unittest.main()
