"""NBT (Named Binary Tag) types, hand-written in include/bedrock/protocol/nbt.hpp."""

from protocol import builtin

package = "bedrock.protocol"


@builtin
class ByteTag:
    pass


@builtin
class ShortTag:
    pass


@builtin
class IntTag:
    pass


@builtin
class Int64Tag:
    pass


@builtin
class FloatTag:
    pass


@builtin
class DoubleTag:
    pass


@builtin
class ByteArrayTag:
    pass


@builtin
class StringTag:
    pass


@builtin
class ListTag:
    pass


@builtin
class CompoundTag:
    pass


@builtin
class IntArrayTag:
    pass


@builtin
class CompoundTagData:
    pass
