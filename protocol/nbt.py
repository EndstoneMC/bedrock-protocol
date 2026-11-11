"""NBT (Named Binary Tag) types, compiler built-ins hand-written in include/bedrock/nbt.hpp."""

from protocol import builtin

package = "bedrock.protocol"


@builtin
class ByteTag: ...


@builtin
class ShortTag: ...


@builtin
class IntTag: ...


@builtin
class Int64Tag: ...


@builtin
class FloatTag: ...


@builtin
class DoubleTag: ...


@builtin
class ByteArrayTag: ...


@builtin
class StringTag: ...


@builtin
class ListTag: ...


@builtin
class CompoundTag: ...


@builtin
class IntArrayTag: ...


@builtin
class CompoundTagData: ...
