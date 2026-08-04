"""`value(name=)` — the wire string, where BDS does not spell it PEP 8.

A name-coded enum reaches the wire as its member's own spelling, and the read
lowercases before the lookup. That makes casing free but the *separator* is not:
BDS writes `DownloadingFinished`, so a PEP 8 `DOWNLOADING_FINISHED` would reject
BDS's own string and put one extra byte behind the length prefix. BDS is not
consistent either -- `persona::PieceType` really does use snake_case -- so the
schema has to be able to say both.
"""

from __future__ import annotations

import unittest

from harness import CompilerCase

PREAMBLE = """
from enum import IntEnum

from protocol import field, packet, uint8, value

package = "bedrock.protocol"
"""

SCHEMA = (
    PREAMBLE
    + """

class ResourcePackResponse(IntEnum, uint8):
    NONE = 0
    REFUSED = 1
    DOWNLOADING_FINISHED = value(3, name="DownloadingFinished")


@packet(id=8)
class ResourcePackClientResponsePacket:
    response: ResourcePackResponse = field(type=str)
"""
)


class WireName(CompilerCase):
    def test_the_cpp_spelling_stays_pep_8(self) -> None:
        header, _ = self.compile(SCHEMA)
        self.assertIn("DOWNLOADING_FINISHED = 3,", header)
        self.assertNotIn("DownloadingFinished = ", header)

    def test_the_write_emits_the_bds_string(self) -> None:
        _, source = self.compile(SCHEMA)
        write = self.body(source, "void Serializer<ResourcePackResponse>::serialize")
        self.assertIn('{E::DOWNLOADING_FINISHED, "DownloadingFinished"}', write)
        self.assertNotIn("DOWNLOADING_FINISHED\"", write)

    def test_the_read_matches_lowercased(self) -> None:
        _, source = self.compile(SCHEMA)
        read = self.body(source, "auto Serializer<ResourcePackResponse>::deserialize")
        self.assertIn('{"downloadingfinished", E::DOWNLOADING_FINISHED}', read)

    def test_a_member_without_the_escape_is_unchanged(self) -> None:
        _, source = self.compile(SCHEMA)
        write = self.body(source, "void Serializer<ResourcePackResponse>::serialize")
        self.assertIn('{E::REFUSED, "REFUSED"}', write)

    def test_an_empty_wire_name_is_rejected(self) -> None:
        message = self.rejects(
            PREAMBLE
            + """

class Kind(IntEnum, uint8):
    A = value(0, name="")
"""
        )
        self.assertIn("value(name=...) must be a non-empty string literal", message)

    def test_a_snake_case_wire_name_is_spellable(self) -> None:
        """BDS is not consistent: persona::PieceType really is snake_case."""
        _, source = self.compile(
            PREAMBLE
            + """

class PieceType(IntEnum, uint8):
    PERSONA_SKELETON = value(0, name="persona_skeleton")


@packet(id=93)
class PlayerSkinPacket:
    piece_type: PieceType = field(type=str)
"""
        )
        write = self.body(source, "void Serializer<PieceType>::serialize")
        self.assertIn('{E::PERSONA_SKELETON, "persona_skeleton"}', write)


if __name__ == "__main__":
    unittest.main()
