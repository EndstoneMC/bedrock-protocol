package dev.endstone.protocol.nbt;

import dev.endstone.protocol.Wire;
import io.netty.buffer.ByteBuf;

public record Int64Tag(long value) implements Tag {
    @Override
    public TagType type() {
        return TagType.INT64;
    }

    @Override
    public void encodeData(ByteBuf buf) {
        Wire.writeVarint64(buf, value);
    }
}
