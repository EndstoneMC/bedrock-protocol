"""A versioned type referenced from another module.

A snapshot namespace holds only the types its *own* file versions, and two
files need not share a snapshot set. So a struct member cannot be spelled
unqualified and left to the enclosing namespace: where the referencing file has
a snapshot the referenced file does not, the name escapes to file scope and
binds the latest-version alias instead -- silently, and only in C++, since the
serializer body qualifies the same reference correctly and the two then
disagree.
"""

from __future__ import annotations

import unittest

from harness import CompilerCase

#: Versioned over {0, 2168} only -- no v1001.
ACTOR = """
from protocol import type, uvarint32, varint32

package = "bedrock.protocol"


@type(until=2168)
class SynchedActorData:
    @type(until=2168)
    class CopyableDataList:
        count: varint32


@type(since=2168)
class SynchedActorData:
    @type(since=2168)
    class CopyableDataList:
        count: uvarint32
"""

#: Versioned over {0, 1001, 2168} -- one snapshot more than the module it
#: imports from.
MOVEMENT = """
from protocol import packet, uvarint32
from protocol.actor import SynchedActorData

package = "bedrock.protocol"


@packet(id=12, until=1001)
class AddPlayerPacket:
    runtime_id: uvarint32
    unpack: SynchedActorData.CopyableDataList


@packet(id=12, since=1001, until=2168)
class AddPlayerPacket:
    runtime_id: uvarint32
    tick: uvarint32
    unpack: SynchedActorData.CopyableDataList


@packet(id=12, since=2168)
class AddPlayerPacket:
    unpack: SynchedActorData.CopyableDataList
"""


class CrossModuleReference(CompilerCase):
    def test_the_member_is_snapshot_qualified(self) -> None:
        header, _ = self.compile(MOVEMENT, imports={"actor": ACTOR})
        v1001 = self.namespace(header, "v1001")
        self.assertIn("base::SynchedActorData::CopyableDataList unpack{};", v1001)
        self.assertNotIn("\n    SynchedActorData::CopyableDataList unpack{};", v1001)

    def test_every_snapshot_names_the_shape_it_means(self) -> None:
        header, _ = self.compile(MOVEMENT, imports={"actor": ACTOR})
        self.assertIn(
            "base::SynchedActorData::CopyableDataList unpack{};",
            self.namespace(header, "base"),
        )
        self.assertIn(
            "v2168::SynchedActorData::CopyableDataList unpack{};",
            self.namespace(header, "v2168"),
        )

    def test_the_member_and_the_serializer_agree(self) -> None:
        """The bug: the .cpp qualified the reference and the header did not, so
        the call passed a v2168 value to a base parameter."""
        header, source = self.compile(MOVEMENT, imports={"actor": ACTOR})
        for snapshot in ("base", "v1001"):
            self.assertIn(
                "base::SynchedActorData::CopyableDataList unpack{};",
                self.namespace(header, snapshot),
            )
        body = self.body(source, "void Serializer<v1001::AddPlayerPacket>::serialize")
        self.assertIn(
            "Serializer<base::SynchedActorData::CopyableDataList>::serialize(stream, value.unpack);",
            body,
        )

    def test_an_unversioned_reference_stays_bare(self) -> None:
        header, _ = self.compile(
            """
from protocol import packet, type, uvarint32

package = "bedrock.protocol"


class Plain:
    n: uvarint32


@packet(id=7, until=2168)
class ThingPacket:
    plain: Plain


@packet(id=7, since=2168)
class ThingPacket:
    plain: Plain
    extra: uvarint32
"""
        )
        self.assertIn("Plain plain{};", self.namespace(header, "base"))
        self.assertNotIn("base::Plain", header)


if __name__ == "__main__":
    unittest.main()
