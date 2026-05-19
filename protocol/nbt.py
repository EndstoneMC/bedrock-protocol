"""NBT (Named Binary Tag) types -- compiler built-ins.

Every tag is hand-written in include/bedrock/nbt.hpp: the leaf tags below, the
recursive Tag union, ListTag, and CompoundTag, plus the codec over them. Each
class here carries `@builtin`, so the compiler references the type by name and
routes it through `Serializer<Name>` without emitting a definition of its own.
The names are declared in wire tag-id order.
"""

from protocol._dsl import builtin

package = "bedrock.protocol"


@builtin
class ByteTag:
    """A single signed byte."""


@builtin
class ShortTag:
    """A signed 16-bit integer."""


@builtin
class IntTag:
    """A signed 32-bit integer, varint-coded."""


@builtin
class LongTag:
    """A signed 64-bit integer, varint-coded."""


@builtin
class FloatTag:
    """A 32-bit float."""


@builtin
class DoubleTag:
    """A 64-bit float."""


@builtin
class ByteArrayTag:
    """A length-prefixed array of signed bytes."""


@builtin
class StringTag:
    """A length-prefixed UTF-8 string."""


@builtin
class ListTag:
    """A length-prefixed, homogeneous sequence of tags."""


@builtin
class CompoundTag:
    """An ordered list of named tags."""


@builtin
class IntArrayTag:
    """A length-prefixed array of varint-coded 32-bit integers."""


@builtin
class LongArrayTag:
    """A length-prefixed array of varint-coded 64-bit integers."""
