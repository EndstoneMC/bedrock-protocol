"""`Literal["..."]` — a length-prefixed constant the wire carries and C++ does not.

BDS's cereal wrote the bound *name* of every enumerator ahead of a tagged member
for a while, so a payload carried a run of constant strings no member accounts
for. A bool literal takes the one-byte wire and an integer needs `field(type=)`;
a string needs neither, since the string wire is already length-prefixed.
"""

from __future__ import annotations

import unittest

from harness import CompilerCase

SOURCE = """
from typing import Literal

from protocol import field, packet, uint8

package = "bedrock.protocol"


@packet(id=9)
class ConstantPacket:
    _raw: Literal["raw"]
    _tip: Literal["tip"]
    kind: uint8
    message: str
"""


class LiteralString(CompilerCase):
    def test_the_constant_declares_no_member(self) -> None:
        header, _ = self.compile(SOURCE)
        self.assertIn("std::uint8_t kind{};", header)
        self.assertNotIn("_raw", header)
        self.assertNotIn("_tip", header)

    def test_the_write_emits_the_string(self) -> None:
        _, source = self.compile(SOURCE)
        body = self.body(source, "void Serializer<ConstantPacket>::serialize")
        self.assertIn('stream.write("raw");', body)
        self.assertIn('stream.write("tip");', body)

    def test_the_read_rejects_anything_else(self) -> None:
        _, source = self.compile(SOURCE)
        body = self.body(source, "Serializer<ConstantPacket>::deserialize")
        self.assertIn('*v != "raw"', body)
        self.assertIn("illegal_byte_sequence", body)

    def test_several_spellings_are_accepted_and_the_first_is_written(self) -> None:
        _, source = self.compile(
            """
from typing import Literal

from protocol import packet

package = "bedrock.protocol"


@packet(id=9)
class ConstantPacket:
    _marker: Literal["systemmessage", "systemMessage"]
"""
        )
        write = self.body(source, "void Serializer<ConstantPacket>::serialize")
        self.assertIn('stream.write("systemmessage");', write)
        read = self.body(source, "Serializer<ConstantPacket>::deserialize")
        self.assertIn('*v != "systemmessage" && *v != "systemMessage"', read)

    def test_a_mixed_literal_is_rejected(self) -> None:
        message = self.rejects(
            """
from typing import Literal

from protocol import packet

package = "bedrock.protocol"


@packet(id=9)
class ConstantPacket:
    _bad: Literal["raw", 3]
"""
        )
        self.assertIn("must all take one type", message)


if __name__ == "__main__":
    unittest.main()
