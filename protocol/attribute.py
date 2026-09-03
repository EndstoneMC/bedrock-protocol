"""Mob attribute algebra: world/attribute/ -- modifiers, operands, AttributeData.
Not the environment attribute system -- world/eas/, in eas.py."""

from enum import IntEnum

from protocol import field, int32, packet
from protocol.actor import ActorRuntimeID, PlayerInputTick

package = "bedrock.protocol"


class AttributeModifierOperation(IntEnum):
    OPERATION_ADDITION = 0
    OPERATION_MULTIPLY_BASE = 1
    OPERATION_MULTIPLY_TOTAL = 2
    OPERATION_CAP = 3
    TOTAL_OPERATIONS = 4
    OPERATION_INVALID = 4


class AttributeOperands(IntEnum):
    OPERAND_MIN = 0
    OPERAND_MAX = 1
    OPERAND_CURRENT = 2
    TOTAL_OPERANDS = 3
    OPERAND_INVALID = 3


class AttributeModifier:
    id: str
    name: str
    amount: float
    operation: AttributeModifierOperation = field(type=int32)
    operand: AttributeOperands = field(type=int32)
    serialize: bool


class AttributeData:
    min_value: float
    max_value: float
    current_value: float
    default_min_value: float
    default_max_value: float
    default_value: float
    name: str
    modifiers: list[AttributeModifier]


@packet(id=29)
class UpdateAttributesPacket:
    runtime_id: ActorRuntimeID
    attribute_data: list[AttributeData]
    tick: PlayerInputTick
