package dev.endstone.protocol;

import io.netty.buffer.ByteBuf;

/** A packet body with its id. */
public interface Packet {
    int packetId();

    void encode(ByteBuf buf);
}
