package dev.endstone.protocol.nbt;

import io.netty.buffer.ByteBuf;

/** A byte tag. */
public record ByteTag(byte value) implements Tag {
    @Override
    public TagType type() {
        return TagType.BYTE;
    }

    @Override
    public void encodeData(ByteBuf buf) {
        buf.writeByte(value);
    }
}
