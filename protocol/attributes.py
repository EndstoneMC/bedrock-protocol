from enum import Enum, IntEnum

from protocol import field, int32, packet, type, uint8, uint32, uvarint32, varint32
from protocol.actor import ActorRuntimeID, PlayerInputTick

package = "bedrock.protocol"


type DimensionType = varint32


class Color255RGBA:
    r: int32
    g: int32
    b: int32
    a: int32


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


class EasingType(Enum, uint32):
    LINEAR = 0
    SPRING = 1
    IN_QUAD = 2
    OUT_QUAD = 3
    IN_OUT_QUAD = 4
    IN_CUBIC = 5
    OUT_CUBIC = 6
    IN_OUT_CUBIC = 7
    IN_QUART = 8
    OUT_QUART = 9
    IN_OUT_QUART = 10
    IN_QUINT = 11
    OUT_QUINT = 12
    IN_OUT_QUINT = 13
    IN_SINE = 14
    OUT_SINE = 15
    IN_OUT_SINE = 16
    IN_EXPO = 17
    OUT_EXPO = 18
    IN_OUT_EXPO = 19
    IN_CIRC = 20
    OUT_CIRC = 21
    IN_OUT_CIRC = 22
    IN_BOUNCE = 23
    OUT_BOUNCE = 24
    IN_OUT_BOUNCE = 25
    IN_BACK = 26
    OUT_BACK = 27
    IN_OUT_BACK = 28
    IN_ELASTIC = 29
    OUT_ELASTIC = 30
    IN_OUT_ELASTIC = 31


@type(since=2192)
class NoiseAlignmentType(IntEnum, uint8):
    MIN_LOCAL_TRANSITION_END = 0


@type(since=2192)
class NoiseAlignment:
    type: NoiseAlignmentType
    value: uvarint32


class BoolAttributeData:
    value: bool
    operation: BoolAttributeOperation = field(type=str)


class FloatAttributeData:
    value: float
    operation: FloatAttributeOperation = field(type=str)
    constraint_min_value: float | None
    constraint_max_value: float | None


class ColorAttributeData:
    value: Color255RGBA
    operation: ColorAttributeOperation = field(type=str)


type AttributeDataVariant = BoolAttributeData | FloatAttributeData | ColorAttributeData


class EnvironmentAttributeData:
    name: str
    from_attribute: AttributeDataVariant | None
    attribute: AttributeDataVariant
    to_attribute: AttributeDataVariant | None
    current_transition_ticks: uint32
    total_transition_ticks: uint32
    easing: EasingType = field(type=str)
    local_transition_ticks: uint32 = field(since=1001)
    noise_transition: bool = field(since=1001)
    noise_alignment: NoiseAlignment = field(since=2192)


class AttributeLayerSettings:
    priority: int32
    weight: float
    enabled: bool
    transitions_paused: bool


class AttributeLayerData:
    name: str
    noise_name: str | None = field(since=1001)
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
    )


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


@packet(id=29, since=2168)
class UpdateAttributesPacket:
    runtime_id: ActorRuntimeID
    attribute_data: list[AttributeData]
    tick: PlayerInputTick
