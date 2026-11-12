package dev.endstone.protocol;

import io.netty.buffer.ByteBuf;

/** Reads one value from a buffer, charging the budget. */
@FunctionalInterface
public interface Decoder<T> {
    T read(ByteBuf buf, DecodeBudget budget);
}
