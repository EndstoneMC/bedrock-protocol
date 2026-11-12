package dev.endstone.protocol.nbt;

import dev.endstone.protocol.Wire;
import io.netty.buffer.ByteBuf;

/** A int tag. */
public record IntTag(int value) implements Tag {
    @Override
    public TagType type() {
        return TagType.INT;
    }

    @Override
    public void encodeData(ByteBuf buf) {
        Wire.writeVarint32(buf, value);
    }
}
