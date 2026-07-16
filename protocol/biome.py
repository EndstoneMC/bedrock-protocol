from protocol import int32, type, uint32

package = "bedrock.protocol"


class FloatRange:
    min: float
    max: float


@type(since=1001)
class NoiseDescriptor:
    name: str
    first_octave: int32
    amplitudes: list[float]


@type(since=1001)
class SerializedNoiseBlockSpecifier:
    noise: str
    threshold: float
    range: FloatRange
    block_runtime_id: uint32


# TODO: confirm against BDS -- the 975 shape's names come from EndstoneMC/protocol-docs
# r26_u2; bedrock-headers only carries the post-981 shape.
@type(until=1001)
class BiomeNoiseGradientSurfaceData:
    non_replaceable_blocks: list[uint32]
    gradient_blocks: list[uint32]
    noise_seed_string: str
    first_octave: int32
    amplitudes: list[float]


@type(since=1001)
class BiomeNoiseGradientSurfaceData:
    non_replaceable_blocks: list[uint32]
    gradient_block_ranges: list[SerializedNoiseBlockSpecifier]
    noise_descriptor: NoiseDescriptor
