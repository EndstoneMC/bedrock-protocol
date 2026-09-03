"""`MEMBER = 8, "High_Pants"` — how BDS spells a member, where the C++ name does not.

A PEP 8 member reaches C++ as `pascal` of itself, and cereal folds an enumerator's
bound name at bind time, so a name-coded enum reaches the wire as that spelling
lowercased: `DownloadingFinished` goes out "downloadingfinished" with no pair
needed. Casing is therefore never something the schema has to carry, and neither
is the separator now that the C++ name has already dropped it. What the schema
does have to say is where BDS keeps a separator the C++ name does not: `EasingType`
is snake all the way down ("in_out_quad"), the EAS operations are screaming
("ALPHA_BLEND"), and persona's `High_Pants` keeps one its neighbours dropped.

Only a plain `Enum` pairs the two: `IntEnum` and `StrEnum` coerce a member to
their own type, so `8, "High_Pants"` is not a value there and the string goes to
`value()` instead.

The reflected `names_v` table is the one the wire uses, so the folded pair lands
there -- for every enum, not just the name-coded ones, which is what lets
`enum_cast` fold its input and be case-insensitive without a predicate. The write
reads the table through `enum_name`; the read keys its own on the same strings
(see test_enum_serializer.py).
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
    DOWNLOADING_FINISHED = 3
    HIGH_PANTS = 8, "High_Pants"


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
    def test_the_cpp_spelling_is_derived_not_the_pair(self) -> None:
        header, _ = self.compile(SCHEMA)
        self.assertIn("DownloadingFinished = 3,", header)
        self.assertIn("HighPants = 8,", header)
        self.assertNotIn("DOWNLOADING_FINISHED = ", header)
        self.assertNotIn("High_Pants = ", header)

    def test_the_reflected_name_is_bds_s_string_folded(self) -> None:
        header, _ = self.compile(SCHEMA)
        names = self.names(header, "ResourcePackResponse")
        self.assertIn('"downloadingfinished",', names)
        self.assertIn('"high_pants",', names)
        self.assertNotIn('"DownloadingFinished",', names)
        self.assertNotIn('"highpants",', names)

    def test_both_directions_carry_the_wire_name(self) -> None:
        """Neither body spells a name: both reach the one table."""
        _, source = self.compile(SCHEMA)
        write = self.body(source, "void Serializer<ResourcePackResponse>::serialize")
        read = self.body(source, "auto Serializer<ResourcePackResponse>::deserialize")
        self.assertIn("enum_name(value)", write)
        self.assertNotIn("High_Pants", write)
        self.assertIn("enum_cast<ResourcePackResponse>(*v", read)

    def test_the_read_names_no_predicate(self) -> None:
        """Every name table is folded, so `enum_cast` folds what it is given and the
        read is case-insensitive with nothing to ask for."""
        _, source = self.compile(SCHEMA)
        read = self.body(source, "auto Serializer<ResourcePackResponse>::deserialize")
        self.assertIn("enum_cast<ResourcePackResponse>(*v)", read)
        self.assertNotIn("case_insensitive", read)

    def test_a_member_without_the_escape_folds_on_its_own(self) -> None:
        header, _ = self.compile(SCHEMA)
        self.assertIn('"refused",', self.names(header, "ResourcePackResponse"))

    def test_a_numeric_enum_reflects_folded_too(self) -> None:
        """One spelling per enum, name-coded or not: `enum_cast` folds its input
        against the table, so a single folded table makes every lookup insensitive."""
        header, _ = self.compile(
            PREAMBLE
            + """

class Kind(Enum, uint8):
    FIRST_ONE = 0


@packet(id=9)
class KindPacket:
    kind: Kind
"""
        )
        self.assertIn('"firstone",', self.names(header, "Kind"))

    def test_a_snake_case_wire_name_is_spellable(self) -> None:
        """BDS is not consistent: persona::PieceType really is snake_case."""
        header, _ = self.compile(
            PREAMBLE
            + """

class PieceType(Enum, uint8):
    SKELETON = 0, "persona_skeleton"


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
    FIRST = 0
    SECOND_ONE = auto(), "Second_One"


@packet(id=9)
class KindPacket:
    kind: Kind = field(type=str)
"""
        )
        self.assertIn("SecondOne = 1,", header)
        self.assertIn('"second_one",', self.names(header, "Kind"))


class ValueSpelling(WireNameCase):
    """`value()` carries the wire name for a base that cannot take a pair, and for
    a member that is also version-gated."""

    GATED = (
        PREAMBLE
        + """

class Kind(IntEnum, uint8):
    FIRST = 0
    SECOND_ONE = value(7, "Second_One", since=1001)


@packet(id=9)
class KindPacket:
    kind: Kind = field(type=str)
"""
    )

    def test_the_second_positional_is_the_wire_name(self) -> None:
        header, _ = self.compile(self.GATED)
        self.assertIn("SecondOne = 7,", header)
        self.assertIn('"second_one",', self.names(header, "v1001::Kind"))

    def test_the_gate_still_applies(self) -> None:
        header, _ = self.compile(self.GATED)
        self.assertNotIn('"second_one",', self.names(header, "base::Kind"))

    def test_the_keyword_spelling_works_too(self) -> None:
        header, _ = self.compile(
            PREAMBLE
            + """

class Kind(IntEnum, uint8):
    FIRST_ONE = value(0, name="First_One")


@packet(id=9)
class KindPacket:
    kind: Kind = field(type=str)
"""
        )
        self.assertIn('"first_one",', self.names(header, "Kind"))


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
