package dev.endstone.protocol.nbt;

import dev.endstone.protocol.DecodeBudget;
import dev.endstone.protocol.DecodeException;
import dev.endstone.protocol.DecodeException.Reason;
import dev.endstone.protocol.Wire;
import io.netty.buffer.ByteBuf;
import java.util.Arrays;
import java.util.Objects;
import org.jspecify.annotations.Nullable;

/** A byte array tag of unsigned elements, 0 to 255; two compare equal when their elements do. */
public record ByteArrayTag(int[] value) implements Tag {
    public ByteArrayTag {
        Objects.requireNonNull(value, "ByteArrayTag.value");
        for (int element : value) {
            if (element < 0 || element > 0xFF) {
                throw new IllegalArgumentException(
                        "ByteArrayTag.value element out of range: " + element);
            }
        }
    }

    @Override
    public TagType type() {
        return TagType.BYTE_ARRAY;
    }

    @Override
    public void encodeData(ByteBuf buf) {
        Wire.writeVarint32(buf, value.length);
        for (int element : value) {
            buf.writeByte(element);
        }
    }

    static ByteArrayTag readBody(ByteBuf buf, DecodeBudget budget) {
        int count = Wire.charge(buf, budget, Wire.readVarint32Count(buf), 1);
        if (count > buf.readableBytes()) {
            throw new DecodeException(Reason.TRUNCATED, buf.readerIndex());
        }
        int[] value = new int[count];
        for (int i = 0; i < count; i++) {
            value[i] = Wire.readUint8(buf);
        }
        return new ByteArrayTag(value);
    }

    @Override
    public boolean equals(@Nullable Object other) {
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
