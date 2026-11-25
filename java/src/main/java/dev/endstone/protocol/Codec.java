package dev.endstone.protocol;

import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

/** Encodes and decodes one message type in one of its encodings. */
public interface Codec<T extends Message> extends Decoder<T> {
  void encode(@NotNull T value, @NotNull ByteBuf buf);

  @Override
  @NotNull
  T decode(@NotNull ByteBuf buf);
}
