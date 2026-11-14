package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufUtils;
import io.netty.buffer.ByteBuf;

public record IntTag(int value) implements Tag {
    @Override
    public TagType type() {
        return TagType.INT;
    }

    @Override
    public void encodeData(ByteBuf buf) {
        ByteBufUtils.writeVarInt(buf, value);
    }
}
