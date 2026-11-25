package dev.endstone.protocol.nbt;

import org.jetbrains.annotations.NotNull;

public sealed interface PrimitiveTag extends Tag permits NumericTag, StringTag {
  @Override
  default @NotNull Tag copy() {
    return this;
  }
}
