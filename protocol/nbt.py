"""NBT (Named Binary Tag) types -- compiler built-ins.

Every tag is hand-written in include/bedrock/nbt.hpp: the leaf tags below, the
recursive Tag union, ListTag, and CompoundTag, plus the codec over them. This
module only declares the names, in wire tag-id order, so packet fields can
spell them.
"""

package = "bedrock.protocol"


class ByteTag:
    """A single signed byte."""


class ShortTag:
    """A signed 16-bit integer."""


class IntTag:
    """A signed 32-bit integer, varint-coded."""


class LongTag:
    """A signed 64-bit integer, varint-coded."""


class FloatTag:
    """A 32-bit float."""


class DoubleTag:
    """A 64-bit float."""


class ByteArrayTag:
    """A length-prefixed array of signed bytes."""


class StringTag:
    """A length-prefixed UTF-8 string."""


class ListTag:
    """A length-prefixed, homogeneous sequence of tags."""


class CompoundTag:
    """An ordered list of named tags."""


class IntArrayTag:
    """A length-prefixed array of varint-coded 32-bit integers."""


class LongArrayTag:
    """A length-prefixed array of varint-coded 64-bit integers."""
