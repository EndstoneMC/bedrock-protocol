package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufUtils;
import dev.endstone.protocol.DecodeBudget;
import dev.endstone.protocol.DecodeException;
import dev.endstone.protocol.DecodeException.Reason;
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
        ByteBufUtils.writeVarInt(buf, value.length);
        for (int element : value) {
            ByteBufUtils.writeVarInt(buf, element);
        }
    }

    static IntArrayTag readBody(ByteBuf buf, DecodeBudget budget) {
        int count =
                ByteBufUtils.charge(
                        buf, budget, ByteBufUtils.readVarint32Count(buf), Integer.BYTES);
        if (count > buf.readableBytes()) {
            throw new DecodeException(Reason.TRUNCATED, buf.readerIndex());
        }
        int[] value = new int[count];
        for (int i = 0; i < count; i++) {
            value[i] = ByteBufUtils.readVarInt(buf);
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
