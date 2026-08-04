"""`field(snapshot=)` — reaching a shape the declaring context has moved past.

BDS cerealised packets one at a time, so one class name meant two wire shapes at
one protocol version, chosen by whichever packet contained it. At 1001 packet 30
carries the cerealised `ItemUseInventoryTransaction` while packet 144 carries the
pre-cereal one. Where BDS gave the two forms separate names they are separate
declarations and nothing here is needed; where it reused the name, the older shape
is still declared over the era before the migration and merely unreachable.

The generated C++ already had both types -- `base::X` beside `v1001::X`, each with
its own `Serializer` -- so this is a frontend gap only: a reference resolved at the
declaring context's snapshot and there was no way to say otherwise.
"""

from __future__ import annotations

import unittest

from harness import CompilerCase

SCHEMA = """
from protocol import field, packet, type, uint8, uvarint32

package = "bedrock.protocol"


@type(until=1001)
class Carried:
    legacy: uvarint32


@type(since=1001)
class Carried:
    cerealised: uint8


@packet(id=30)
class CerealPacket:
    carried: Carried


@packet(id=144)
class LegacyPacket:
    carried: Carried = field(snapshot=975)
"""


class SnapshotPin(CompilerCase):
    def test_the_unpinned_field_follows_its_own_snapshot(self) -> None:
        _, source = self.compile(SCHEMA)
        body = self.body(source, "void Serializer<v1001::CerealPacket>::serialize")
        self.assertIn("Serializer<v1001::Carried>", body)

    def test_the_pinned_field_reaches_the_older_shape(self) -> None:
        """Same snapshot, same name, the other shape."""
        _, source = self.compile(SCHEMA)
        body = self.body(source, "void Serializer<v1001::LegacyPacket>::serialize")
        self.assertIn("Serializer<base::Carried>", body)
        self.assertNotIn("v1001::Carried", body)

    def test_the_member_type_is_pinned_too(self) -> None:
        """The v1001 view of the packet, where the two shapes actually differ."""
        header, _ = self.compile(SCHEMA)
        v1001 = header.index("namespace v1001 {")
        start = header.index("struct LegacyPacket {", v1001)
        self.assertIn("base::Carried carried{};", header[start : start + 200])

    def test_a_pin_through_an_optional(self) -> None:
        _, source = self.compile(
            SCHEMA.replace(
                "    carried: Carried = field(snapshot=975)",
                "    carried: Carried | None = field(snapshot=975)",
            )
        )
        body = self.body(source, "void Serializer<v1001::LegacyPacket>::serialize")
        self.assertIn("Serializer<base::Carried>", body)

    def test_a_pin_through_a_list(self) -> None:
        _, source = self.compile(
            SCHEMA.replace(
                "    carried: Carried = field(snapshot=975)",
                "    carried: list[Carried] = field(snapshot=975)",
            )
        )
        body = self.body(source, "void Serializer<v1001::LegacyPacket>::serialize")
        self.assertIn("Serializer<base::Carried>", body)

    def test_a_pin_on_a_primitive_is_rejected(self) -> None:
        """Nothing to resolve: a primitive has no per-snapshot shape."""
        message = self.rejects(
            SCHEMA.replace(
                "    carried: Carried = field(snapshot=975)",
                "    carried: uint8 = field(snapshot=975)",
            )
        )
        self.assertIn("pins a struct or enum reference", message)


if __name__ == "__main__":
    unittest.main()
