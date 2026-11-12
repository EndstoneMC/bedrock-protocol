package dev.endstone.protocol.nbt;

import io.netty.buffer.ByteBuf;

public record FloatTag(float value) implements Tag {
    @Override
    public TagType type() {
        return TagType.FLOAT;
    }

    @Override
    public void encodeData(ByteBuf buf) {
        buf.writeFloatLE(value);
    }
}
