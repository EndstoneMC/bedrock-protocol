package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufCodec;
import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

public record DoubleTag(double value) implements NumericTag {
    public static final @NotNull TagType<DoubleTag> TYPE =
            buf -> valueOf(ByteBufCodec.readDoubleLE(buf));

    public static @NotNull DoubleTag valueOf(double value) {
        return new DoubleTag(value);
    }

    @Override
    public void encode(@NotNull ByteBuf buf) {
        buf.writeDoubleLE(value);
    }

    @Override
    public byte getId() {
        return TAG_DOUBLE;
    }

    @Override
    public @NotNull TagType<DoubleTag> getType() {
        return TYPE;
    }

    @Override
    public @NotNull DoubleTag copy() {
        return this;
    }

    @Override
    public byte byteValue() {
        return (byte) ((int) Math.floor(value) & 255);
    }

    @Override
    public short shortValue() {
        return (short) ((int) Math.floor(value) & 65535);
    }

    @Override
    public int intValue() {
        return (int) Math.floor(value);
    }

    @Override
    public long longValue() {
        return (long) Math.floor(value);
    }

    @Override
    public float floatValue() {
        return (float) value;
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
