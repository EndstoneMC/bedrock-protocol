package dev.endstone.protocol.nbt;

import org.jetbrains.annotations.NotNull;

public sealed interface CollectionTag extends Tag permits ByteArrayTag, IntArrayTag, ListTag {
  int size();

  @NotNull
  Tag get(int index);
}
