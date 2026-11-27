"""Packets and types relating to mob and environment attributes."""

from enum import IntEnum

from protocol import field, int32, packet, type, uint8, uint32, uvarint32, value
from protocol.actor import ActorRuntimeID, PlayerInputTick
from protocol.common import Color255RGBA, DimensionType, EasingType

package = "bedrock.protocol"
java_package = "dev.endstone.protocol"
go_package = "github.com/EndstoneMC/bedrock-protocol/go/protocol"


class AttributeModifierOperation(IntEnum, int32):
    OPERATION_ADDITION = 0
    OPERATION_MULTIPLY_BASE = 1
    OPERATION_MULTIPLY_TOTAL = 2
    OPERATION_CAP = 3
    TOTAL_OPERATIONS = 4
    OPERATION_INVALID = value(4, synonym=True)


class AttributeOperands(IntEnum, int32):
    OPERAND_MIN = 0
    OPERAND_MAX = 1
    OPERAND_CURRENT = 2
    TOTAL_OPERANDS = 3
    OPERAND_INVALID = value(3, synonym=True)


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
    with field(since=729):
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


class BoolAttributeOperation(IntEnum, int32):
    OVERRIDE = 0
    ALPHA_BLEND = 1, "ALPHA_BLEND"
    AND = 2
    NAND = 3
    OR = 4
    NOR = 5
    XOR = 6
    XNOR = 7


class FloatAttributeOperation(IntEnum, int32):
    OVERRIDE = 0
    ALPHA_BLEND = 1, "ALPHA_BLEND"
    ADD = 2
    SUBTRACT = 3
    MULTIPLY = 4
    MINIMUM = 5
    MAXIMUM = 6


class ColorAttributeOperation(IntEnum, int32):
    OVERRIDE = 0
    ALPHA_BLEND = 1, "ALPHA_BLEND"
    ADD = 2
    SUBTRACT = 3
    MULTIPLY = 4


@type(since=2259)
class StringAttributeOperation(IntEnum, int32):
    OVERRIDE = 0


@type(since=2193)
class NoiseAlignmentType(IntEnum, uint8):
    MIN_LOCAL_TRANSITION_END = 0


@type(since=2193)
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


@type(since=2259)
class StringAttributeData:
    value: str
    operation: StringAttributeOperation = field(type=str)


with type(until=2259):
    type AttributeDataVariant = BoolAttributeData | FloatAttributeData | ColorAttributeData

with type(since=2259):
    type AttributeDataVariant = BoolAttributeData | FloatAttributeData | ColorAttributeData | StringAttributeData


@type(since=2225)
class ConstantAttributeData:
    attribute: AttributeDataVariant


@type(since=2225)
class TransitionSettingsData:
    total_transition_ticks: uvarint32
    current_transition_ticks: uvarint32
    easing: EasingType
    clock_name: str


@type(since=2225)
class TransitionAttributeData:
    from_attribute: AttributeDataVariant
    to_attribute: AttributeDataVariant
    settings: TransitionSettingsData


@type(since=2225)
class NoiseTransitionSettingsData:
    total_transition_ticks: uvarint32
    current_transition_ticks: uvarint32
    easing: EasingType
    clock_name: str
    local_transition_ticks: uvarint32
    noise_name: str
    noise_alignment: NoiseAlignment


@type(since=2225)
class NoiseTransitionAttributeData:
    from_attribute: AttributeDataVariant
    to_attribute: AttributeDataVariant
    settings: NoiseTransitionSettingsData


type AttributePayloadVariant = ConstantAttributeData | TransitionAttributeData | NoiseTransitionAttributeData


@type(until=2225)
class EnvironmentAttributeData:
    name: str
    from_attribute: AttributeDataVariant | None
    attribute: AttributeDataVariant
    to_attribute: AttributeDataVariant | None
    current_transition_ticks: uint32
    total_transition_ticks: uint32
    easing: EasingType = field(type=str)
    with field(since=1001):
        local_transition_ticks: uint32
        noise_transition: bool
    noise_alignment: NoiseAlignment = field(since=2193)


@type(since=2225)
class EnvironmentAttributeData:
    name: str
    payload: AttributePayloadVariant


class AttributeLayerSettings:
    priority: int32
    weight: float | str = field(until=975)
    weight: float = field(since=975)
    enabled: bool
    transitions_paused: bool


class AttributeLayerData:
    name: str
    noise_name: str | None = field(since=1001, until=2225)
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
