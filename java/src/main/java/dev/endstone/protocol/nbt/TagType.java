package dev.endstone.protocol.nbt;

import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

/** Decodes the payload of one kind of tag. */
@FunctionalInterface
public interface TagType<T extends Tag> {
  @NotNull
  T decode(@NotNull ByteBuf buf);
}
