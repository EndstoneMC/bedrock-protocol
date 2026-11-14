package dev.endstone.protocol;

import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

/** A packet body with its id. */
public interface Packet {
    int packetId();

    void serialize(@NotNull ByteBuf buf);
}
