"""`MEMBER = 3, "DownloadingFinished"` — the wire string, where BDS does not spell it PEP 8.

A name-coded enum reaches the wire as its member's own spelling, and the read
lowercases before the lookup. That makes casing free but the *separator* is not:
BDS writes `DownloadingFinished`, so a PEP 8 `DOWNLOADING_FINISHED` would reject
BDS's own string and put one extra byte behind the length prefix. BDS is not
consistent either -- `persona::PieceType` really does use snake_case -- so the
schema has to be able to say both.

Only a plain `Enum` pairs the two: `IntEnum` and `StrEnum` coerce a member to
their own type, so `3, "DownloadingFinished"` is not a value there and the
string goes to `value()` instead.

The reflected `names_v` table is the one the wire uses, so the paired string
lands there. The write reads it through `enum_name`; the read keys its own
table, since the reflection helpers are the downstream API and a scan over them
is linear (see test_enum_serializer.py).
"""

from __future__ import annotations

import unittest

from harness import CompilerCase

PREAMBLE = """
from enum import Enum, IntEnum, auto

from protocol import field, packet, uint8, value

package = "bedrock.protocol"
"""

SCHEMA = (
    PREAMBLE
    + """

class ResourcePackResponse(Enum, uint8):
    NONE = 0
    REFUSED = 1
    DOWNLOADING_FINISHED = 3, "DownloadingFinished"


@packet(id=8)
class ResourcePackClientResponsePacket:
    response: ResourcePackResponse = field(type=str)
"""
)


class WireNameCase(CompilerCase):
    def names(self, header: str, qualified: str) -> str:
        """The reflected name table for one enum."""
        start = header.index(f"names_v<{qualified}>")
        return header[start : header.index("}};", start)]


class WireName(WireNameCase):
    def test_the_cpp_spelling_stays_pep_8(self) -> None:
        header, _ = self.compile(SCHEMA)
        self.assertIn("DOWNLOADING_FINISHED = 3,", header)
        self.assertNotIn("DownloadingFinished = ", header)

    def test_the_reflected_name_is_the_bds_string(self) -> None:
        header, _ = self.compile(SCHEMA)
        names = self.names(header, "ResourcePackResponse")
        self.assertIn('"DownloadingFinished",', names)
        self.assertNotIn('"DOWNLOADING_FINISHED",', names)

    def test_both_directions_carry_the_wire_name(self) -> None:
        """The write reaches it through the reflected table; the read keys its
        own on the lowercased form."""
        _, source = self.compile(SCHEMA)
        write = self.body(source, "void Serializer<ResourcePackResponse>::serialize")
        read = self.body(source, "auto Serializer<ResourcePackResponse>::deserialize")
        self.assertIn("enum_name(value)", write)
        self.assertNotIn("DownloadingFinished", write)
        self.assertIn('{"downloadingfinished", E::DOWNLOADING_FINISHED}', read)

    def test_the_read_is_case_insensitive(self) -> None:
        """BDS lowercases the incoming string before its own lookup, so the
        keys are lowercased and the incoming string is folded to match."""
        _, source = self.compile(SCHEMA)
        read = self.body(source, "auto Serializer<ResourcePackResponse>::deserialize")
        self.assertIn("std::tolower", read)
        self.assertIn('{"refused", E::REFUSED}', read)

    def test_a_member_without_the_escape_is_unchanged(self) -> None:
        header, _ = self.compile(SCHEMA)
        self.assertIn('"REFUSED",', self.names(header, "ResourcePackResponse"))

    def test_a_snake_case_wire_name_is_spellable(self) -> None:
        """BDS is not consistent: persona::PieceType really is snake_case."""
        header, _ = self.compile(
            PREAMBLE
            + """

class PieceType(Enum, uint8):
    PERSONA_SKELETON = 0, "persona_skeleton"


@packet(id=93)
class PlayerSkinPacket:
    piece_type: PieceType = field(type=str)
"""
        )
        self.assertIn('"persona_skeleton",', self.names(header, "PieceType"))

    def test_auto_pairs_with_a_wire_name(self) -> None:
        header, _ = self.compile(
            PREAMBLE
            + """

class Kind(Enum, uint8):
    FIRST = 0, "First"
    SECOND = auto(), "Second"


@packet(id=9)
class KindPacket:
    kind: Kind = field(type=str)
"""
        )
        self.assertIn("SECOND = 1,", header)
        self.assertIn('"Second",', self.names(header, "Kind"))


class ValueSpelling(WireNameCase):
    """`value()` carries the wire name for a base that cannot take a pair, and for
    a member that is also version-gated."""

    GATED = (
        PREAMBLE
        + """

class Kind(IntEnum, uint8):
    FIRST = 0
    SECOND = value(7, "Second", since=1001)


@packet(id=9)
class KindPacket:
    kind: Kind = field(type=str)
"""
    )

    def test_the_second_positional_is_the_wire_name(self) -> None:
        header, _ = self.compile(self.GATED)
        self.assertIn("SECOND = 7,", header)
        self.assertIn('"Second",', self.names(header, "v1001::Kind"))

    def test_the_gate_still_applies(self) -> None:
        header, _ = self.compile(self.GATED)
        self.assertNotIn('"Second",', self.names(header, "base::Kind"))

    def test_the_keyword_spelling_works_too(self) -> None:
        header, _ = self.compile(
            PREAMBLE
            + """

class Kind(IntEnum, uint8):
    FIRST = value(0, name="First")


@packet(id=9)
class KindPacket:
    kind: Kind = field(type=str)
"""
        )
        self.assertIn('"First",', self.names(header, "Kind"))


class Rejections(CompilerCase):
    def test_a_pair_needs_a_plain_enum_base(self) -> None:
        """IntEnum would coerce the member through `int(3, "A")`."""
        message = self.rejects(
            PREAMBLE
            + """

class Kind(IntEnum, uint8):
    A = 0, "A"
"""
        )
        self.assertIn("only a plain Enum pairs a value with a wire name", message)

    def test_an_empty_wire_name_is_rejected(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

class Kind(Enum, uint8):
    A = 0, ""
"""
        )
        self.assertIn("wire name must be a non-empty string literal", message)

    def test_a_non_string_wire_name_is_rejected(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

class Kind(Enum, uint8):
    A = 0, 1
"""
        )
        self.assertIn("wire name must be a string literal", message)

    def test_a_longer_tuple_is_rejected(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

class Kind(Enum, uint8):
    A = 0, "A", "extra"
"""
        )
        self.assertIn("(value, wire name) pair", message)


if __name__ == "__main__":
    unittest.main()
