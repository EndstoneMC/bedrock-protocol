package dev.endstone.protocol.nbt;

import dev.endstone.protocol.DecodeBudget;
import dev.endstone.protocol.DecodeException;
import dev.endstone.protocol.DecodeException.Reason;
import dev.endstone.protocol.Wire;
import io.netty.buffer.ByteBuf;
import java.util.Arrays;

/** A byte array tag; two compare equal when their bytes do. */
public record ByteArrayTag(byte[] value) implements Tag {
    @Override
    public TagType type() {
        return TagType.BYTE_ARRAY;
    }

    @Override
    public void encodeData(ByteBuf buf) {
        Wire.writeVarint32(buf, value.length);
        buf.writeBytes(value);
    }

    static ByteArrayTag readData(ByteBuf buf, DecodeBudget budget) {
        int count = Wire.charge(buf, budget, Wire.readVarint32Count(buf), 1);
        if (count > buf.readableBytes()) {
            throw new DecodeException(Reason.TRUNCATED, buf.readerIndex());
        }
        byte[] value = new byte[count];
        buf.readBytes(value);
        return new ByteArrayTag(value);
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof ByteArrayTag tag && Arrays.equals(value, tag.value);
    }

    @Override
    public int hashCode() {
        return Arrays.hashCode(value);
    }

    @Override
    public String toString() {
        return "ByteArrayTag[value=" + Arrays.toString(value) + "]";
    }
}
