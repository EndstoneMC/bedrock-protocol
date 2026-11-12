package dev.endstone.protocol.nbt;

import io.netty.buffer.ByteBuf;

/** A byte tag holding an unsigned value, 0 to 255. */
public record ByteTag(int value) implements Tag {
    public ByteTag {
        if (value < 0 || value > 0xFF) {
            throw new IllegalArgumentException("ByteTag.value out of range: " + value);
        }
    }

    @Override
    public TagType type() {
        return TagType.BYTE;
    }

    @Override
    public void encodeData(ByteBuf buf) {
        buf.writeByte(value);
    }
}
