"""`Literal[Enum.MEMBER]` — a constant spelled as the enumerator BDS pinned.

cereal's `bindConst` on a compound factory declares a member whose value is fixed at
compile time, so the tag inside a variant alternative is a constant rather than a
field. Naming the enumerator says which one without also spelling a width: the enum's
underlying type derives the wire exactly as it does for an enum-typed field.
"""

from __future__ import annotations

import unittest

from harness import CompilerCase

SOURCE = """
from enum import IntEnum
from typing import Literal

from protocol import packet, uint8, uvarint32

package = "bedrock.protocol"


class ActionType(IntEnum, uint8):
    TAKE = 0
    DROP = 3


@packet(id=9)
class ConstantPacket:
    action_type: Literal[ActionType.DROP]
    payload: uvarint32
"""


class LiteralEnum(CompilerCase):
    def test_the_constant_declares_no_member(self) -> None:
        header, _ = self.compile(SOURCE)
        self.assertIn("std::uint32_t payload{};", header)
        self.assertNotIn("action_type", header)

    def test_the_write_emits_the_number_at_the_underlying_width(self) -> None:
        _, source = self.compile(SOURCE)
        body = self.body(source, "void Serializer<ConstantPacket>::serialize")
        self.assertIn("stream.write<std::uint8_t>(3);", body)

    def test_the_read_rejects_anything_else(self) -> None:
        _, source = self.compile(SOURCE)
        body = self.body(source, "Serializer<ConstantPacket>::deserialize")
        self.assertIn("*v != 3", body)
        self.assertIn("illegal_byte_sequence", body)

    def test_a_wide_underlying_compresses_the_way_an_enum_field_does(self) -> None:
        _, source = self.compile(
            """
from enum import IntEnum
from typing import Literal

from protocol import packet, uint32

package = "bedrock.protocol"


class ActionType(IntEnum, uint32):
    DROP = 3


@packet(id=9)
class ConstantPacket:
    action_type: Literal[ActionType.DROP]
"""
        )
        body = self.body(source, "void Serializer<ConstantPacket>::serialize")
        self.assertIn("stream.writeVarInt<std::uint32_t>(3);", body)

    def test_a_sibling_nested_enum_is_reached_bare(self) -> None:
        _, source = self.compile(
            """
from enum import IntEnum
from typing import Literal

from protocol import packet, uint8

package = "bedrock.protocol"


class Owner:
    class ActionType(IntEnum, uint8):
        TAKE = 0
        DROP = 3

    class TakeAction:
        action_type: Literal[ActionType.TAKE]

    class DropAction:
        action_type: Literal[ActionType.DROP]


@packet(id=9)
class ConstantPacket:
    action: Owner.TakeAction | Owner.DropAction
"""
        )
        body = self.body(source, "void Serializer<Owner::DropAction>::serialize")
        self.assertIn("stream.write<std::uint8_t>(3);", body)

    def test_an_unknown_member_is_rejected(self) -> None:
        message = self.rejects(
            """
from enum import IntEnum
from typing import Literal

from protocol import packet, uint8

package = "bedrock.protocol"


class ActionType(IntEnum, uint8):
    TAKE = 0


@packet(id=9)
class ConstantPacket:
    action_type: Literal[ActionType.PLACE]
"""
        )
        self.assertIn("Enum.MEMBER", message)


if __name__ == "__main__":
    unittest.main()
