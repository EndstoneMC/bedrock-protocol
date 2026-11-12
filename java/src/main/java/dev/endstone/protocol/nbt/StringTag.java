package dev.endstone.protocol.nbt;

import dev.endstone.protocol.Wire;
import io.netty.buffer.ByteBuf;
import java.util.Objects;

public record StringTag(String value) implements Tag {
    public StringTag {
        Objects.requireNonNull(value, "StringTag.value");
    }

    @Override
    public TagType type() {
        return TagType.STRING;
    }

    @Override
    public void encodeData(ByteBuf buf) {
        Wire.writeStr(buf, value);
    }
}
