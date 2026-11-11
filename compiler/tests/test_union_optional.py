"""`X | None` is an optional; `Union[X, None]` stays a union.

The two encode different bytes rather than one shape spelled twice. An optional
writes a presence byte, true when the payload follows; a union writes the
uvarint32 index of its case, and in `Union[X, None]` the payload is case 0. So
present is 0x01 as an optional and 0x00 as a union, and picking the wrong one
inverts every body. DisconnectPacket's cerealised messages are the live case.
"""

from __future__ import annotations

import unittest

from harness import CompilerCase

PREAMBLE = """
from typing import Union

from protocol import packet, uvarint32

package = "bedrock.protocol"


class Messages:
    message: str
"""


class UnionOverOptional(CompilerCase):
    def test_two_cases_with_none_default_to_an_optional(self) -> None:
        header, source = self.compile(
            PREAMBLE
            + """

@packet(id=5)
class ThingPacket:
    messages: Messages | None
"""
        )
        self.assertIn("std::optional<Messages> messages{};", header)
        self.assertIn("stream.write<bool>(value.messages.has_value());", source)

    def test_union_keeps_the_case_index(self) -> None:
        header, source = self.compile(
            PREAMBLE
            + """

@packet(id=5)
class ThingPacket:
    messages: Union[Messages, None]
"""
        )
        self.assertIn("std::variant<Messages, std::monostate> messages{};", header)
        self.assertIn("stream.writeVarInt<std::uint32_t>((value.messages).index());", source)
        self.assertNotIn("has_value()", source)

    def test_the_none_case_keeps_its_declared_position(self) -> None:
        header, _ = self.compile(
            PREAMBLE
            + """

@packet(id=5)
class ThingPacket:
    messages: Union[None, Messages]
"""
        )
        self.assertIn("std::variant<std::monostate, Messages> messages{};", header)

    def test_more_than_two_cases_are_a_union_either_way(self) -> None:
        bar, _ = self.compile(
            PREAMBLE
            + """

@packet(id=5)
class ThingPacket:
    messages: None | Messages | uvarint32
"""
        )
        subscript, _ = self.compile(
            PREAMBLE
            + """

@packet(id=5)
class ThingPacket:
    messages: Union[None, Messages, uvarint32]
"""
        )
        self.assertIn("std::variant<std::monostate, Messages, std::uint32_t> messages{};", bar)
        self.assertIn("std::variant<std::monostate, Messages, std::uint32_t> messages{};", subscript)


if __name__ == "__main__":
    unittest.main()
