from enum import IntEnum

from protocol import field, int32, packet, type, uint32, uvarint32, uvarint64
from protocol.actor import ActorRuntimeID
from protocol.common import Color255RGBA
from protocol.dimension import DimensionType

package = "bedrock.protocol"


@type(since=544)
class AttributeModifierOperation(IntEnum):
    OPERATION_ADDITION = 0
    OPERATION_MULTIPLY_BASE = 1
    OPERATION_MULTIPLY_TOTAL = 2
    OPERATION_CAP = 3


@type(since=544)
class AttributeOperands(IntEnum):
    OPERAND_MIN = 0
    OPERAND_MAX = 1
    OPERAND_CURRENT = 2


@type(since=544)
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
    default_min_value: float = field(since=729)
    default_max_value: float = field(since=729)
    default_value: float
    name: str
    modifiers: list[AttributeModifier] = field(since=544)


@packet(id=29)
class UpdateAttributesPacket:
    runtime_id: ActorRuntimeID
    attribute_data: list[AttributeData]
    tick: uvarint64 = field(since=419)


class BoolAttributeOperation(IntEnum):
    OVERRIDE = 0
    ALPHA_BLEND = 1
    AND = 2
    NAND = 3
    OR = 4
    NOR = 5
    XOR = 6
    XNOR = 7


class FloatAttributeOperation(IntEnum):
    OVERRIDE = 0
    ALPHA_BLEND = 1
    ADD = 2
    SUBTRACT = 3
    MULTIPLY = 4
    MINIMUM = 5
    MAXIMUM = 6


class ColorAttributeOperation(IntEnum):
    OVERRIDE = 0
    ALPHA_BLEND = 1
    ADD = 2
    SUBTRACT = 3
    MULTIPLY = 4


class BoolAttributeData:
    value: bool
    operation: BoolAttributeOperation = field(type=str)


class FloatAttributeData:
    value: float
    operation: FloatAttributeOperation = field(type=str)
    constraint_min_value: float | None
    constraint_max_value: float | None


class ColorAttributeData:
    value: Color255RGBA = field(tag=uvarint32)
    operation: ColorAttributeOperation = field(type=str)


type AttributeDataVariant = BoolAttributeData | FloatAttributeData | ColorAttributeData


class EnvironmentAttributeData:
    name: str
    from_attribute: AttributeDataVariant | None = field(tag=uvarint32)
    attribute: AttributeDataVariant = field(tag=uvarint32)
    to_attribute: AttributeDataVariant | None = field(tag=uvarint32)
    current_transition_ticks: uint32
    total_transition_ticks: uint32
    easing: str


class AttributeLayerSettings:
    priority: int32
    weight: float
    enabled: bool
    transitions_paused: bool


class AttributeLayerData:
    name: str
    dimension_id: DimensionType
    settings: AttributeLayerSettings
    attributes: list[EnvironmentAttributeData]


class UpdateAttributeLayersData:
    attribute_layers: list[AttributeLayerData]


class UpdateAttributeLayerSettingsData:
    layer_name: str
    layer_dimension_id: DimensionType
    attribute_layer_settings: AttributeLayerSettings


class UpdateEnvironmentAttributesData:
    layer_name: str
    layer_dimension_id: DimensionType
    attributes: list[EnvironmentAttributeData]


class RemoveEnvironmentAttributesData:
    layer_name: str
    layer_dimension_id: DimensionType
    attributes: list[str]


@packet(id=345, since=944)
class ClientboundAttributeLayerSyncPacket:
    data: (
        UpdateAttributeLayersData
        | UpdateAttributeLayerSettingsData
        | UpdateEnvironmentAttributesData
        | RemoveEnvironmentAttributesData
    ) = field(tag=uvarint32)
