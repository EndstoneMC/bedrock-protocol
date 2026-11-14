package dev.endstone.protocol;

import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

/** A generated message: an immutable value and its encoding. */
public interface Message {
    void encode(@NotNull ByteBuf buf);
}
