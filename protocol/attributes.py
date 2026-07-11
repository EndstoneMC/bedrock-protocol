from enum import IntEnum

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
    easing: str
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
