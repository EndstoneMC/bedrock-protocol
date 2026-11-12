package dev.endstone.protocol.nbt;

import io.netty.buffer.ByteBuf;

/** A short tag. */
public record ShortTag(short value) implements Tag {
    @Override
    public TagType type() {
        return TagType.SHORT;
    }

    @Override
    public void encodeData(ByteBuf buf) {
        buf.writeShortLE(value);
    }
}
