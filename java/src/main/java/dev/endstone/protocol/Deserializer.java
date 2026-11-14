package dev.endstone.protocol;

import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

/** Deserializes one value from a buffer. */
@FunctionalInterface
public interface Deserializer<T> {
    T deserialize(@NotNull ByteBuf buf);
}
