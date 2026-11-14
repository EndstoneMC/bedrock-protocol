package dev.endstone.protocol;

import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

/** Decodes one value from a buffer. */
@FunctionalInterface
public interface Decoder<T> {
    T decode(@NotNull ByteBuf buf);
}
