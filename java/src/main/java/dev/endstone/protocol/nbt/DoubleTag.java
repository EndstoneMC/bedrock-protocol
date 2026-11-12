package dev.endstone.protocol.nbt;

import io.netty.buffer.ByteBuf;

/** A double tag. */
public record DoubleTag(double value) implements Tag {
    @Override
    public TagType type() {
        return TagType.DOUBLE;
    }

    @Override
    public void encodeData(ByteBuf buf) {
        buf.writeDoubleLE(value);
    }
}
