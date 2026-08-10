from enum import Enum, IntEnum

from protocol import field, int32, packet, uint32, varint32

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
    LINEAR = 0, "linear"
    SPRING = 1, "spring"
    IN_QUAD = 2, "in_quad"
    OUT_QUAD = 3, "out_quad"
    IN_OUT_QUAD = 4, "in_out_quad"
    IN_CUBIC = 5, "in_cubic"
    OUT_CUBIC = 6, "out_cubic"
    IN_OUT_CUBIC = 7, "in_out_cubic"
    IN_QUART = 8, "in_quart"
    OUT_QUART = 9, "out_quart"
    IN_OUT_QUART = 10, "in_out_quart"
    IN_QUINT = 11, "in_quint"
    OUT_QUINT = 12, "out_quint"
    IN_OUT_QUINT = 13, "in_out_quint"
    IN_SINE = 14, "in_sine"
    OUT_SINE = 15, "out_sine"
    IN_OUT_SINE = 16, "in_out_sine"
    IN_EXPO = 17, "in_expo"
    OUT_EXPO = 18, "out_expo"
    IN_OUT_EXPO = 19, "in_out_expo"
    IN_CIRC = 20, "in_circ"
    OUT_CIRC = 21, "out_circ"
    IN_OUT_CIRC = 22, "in_out_circ"
    IN_BOUNCE = 23, "in_bounce"
    OUT_BOUNCE = 24, "out_bounce"
    IN_OUT_BOUNCE = 25, "in_out_bounce"
    IN_BACK = 26, "in_back"
    OUT_BACK = 27, "out_back"
    IN_OUT_BACK = 28, "in_out_back"
    IN_ELASTIC = 29, "in_elastic"
    OUT_ELASTIC = 30, "out_elastic"
    IN_OUT_ELASTIC = 31, "in_out_elastic"


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
