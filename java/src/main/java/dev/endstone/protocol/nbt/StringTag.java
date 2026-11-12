package dev.endstone.protocol.nbt;

import dev.endstone.protocol.Wire;
import io.netty.buffer.ByteBuf;

/** A string tag. */
public record StringTag(String value) implements Tag {
    @Override
    public TagType type() {
        return TagType.STRING;
    }

    @Override
    public void encodeData(ByteBuf buf) {
        Wire.writeStr(buf, value);
    }
}
