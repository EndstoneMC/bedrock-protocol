package dev.endstone.protocol.nbt;

import dev.endstone.protocol.DecodeBudget;
import dev.endstone.protocol.DecodeException;
import dev.endstone.protocol.DecodeException.Reason;
import dev.endstone.protocol.Wire;
import io.netty.buffer.ByteBuf;
import java.util.Arrays;
import java.util.Objects;
import org.jspecify.annotations.Nullable;

/** An int array tag; two compare equal when their ints do. */
public record IntArrayTag(int[] value) implements Tag {
    public IntArrayTag {
        Objects.requireNonNull(value, "IntArrayTag.value");
    }

    @Override
    public TagType type() {
        return TagType.INT_ARRAY;
    }

    @Override
    public void encodeData(ByteBuf buf) {
        Wire.writeVarint32(buf, value.length);
        for (int element : value) {
            Wire.writeVarint32(buf, element);
        }
    }

    static IntArrayTag readBody(ByteBuf buf, DecodeBudget budget) {
        int count = Wire.charge(buf, budget, Wire.readVarint32Count(buf), Integer.BYTES);
        if (count > buf.readableBytes()) {
            throw new DecodeException(Reason.TRUNCATED, buf.readerIndex());
        }
        int[] value = new int[count];
        for (int i = 0; i < count; i++) {
            value[i] = Wire.readVarint32(buf);
        }
        return new IntArrayTag(value);
    }

    @Override
    public boolean equals(@Nullable Object other) {
        return other instanceof IntArrayTag tag && Arrays.equals(value, tag.value);
    }

    @Override
    public int hashCode() {
        return Arrays.hashCode(value);
    }

    @Override
    public String toString() {
        return "IntArrayTag[value=" + Arrays.toString(value) + "]";
    }
}
