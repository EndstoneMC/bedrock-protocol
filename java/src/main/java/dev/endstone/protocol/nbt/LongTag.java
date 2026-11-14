package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufCodec;
import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

public record LongTag(long value) implements NumericTag {
    public static final @NotNull TagType<LongTag> TYPE =
            buf -> valueOf(ByteBufCodec.readVarLong(buf));

    public static @NotNull LongTag valueOf(long value) {
        return new LongTag(value);
    }

    @Override
    public void serialize(@NotNull ByteBuf buf) {
        ByteBufCodec.writeVarLong(buf, value);
    }

    @Override
    public byte getId() {
        return TAG_LONG;
    }

    @Override
    public @NotNull TagType<LongTag> getType() {
        return TYPE;
    }

    @Override
    public @NotNull LongTag copy() {
        return this;
    }

    @Override
    public byte byteValue() {
        return (byte) (value & 255);
    }

    @Override
    public short shortValue() {
        return (short) (value & 65535);
    }

    @Override
    public int intValue() {
        return (int) value;
    }

    @Override
    public long longValue() {
        return value;
    }

    @Override
    public float floatValue() {
        return value;
    }

    @Override
    public double doubleValue() {
        return value;
    }

    @Override
    public @NotNull Number numberValue() {
        return value;
    }
}
