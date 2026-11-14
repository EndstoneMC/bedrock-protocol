package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufCodec;
import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

public record FloatTag(float value) implements NumericTag {
    public static final @NotNull TagType<FloatTag> TYPE =
            buf -> valueOf(ByteBufCodec.readFloatLE(buf));

    public static @NotNull FloatTag valueOf(float value) {
        return new FloatTag(value);
    }

    @Override
    public void serialize(@NotNull ByteBuf buf) {
        buf.writeFloatLE(value);
    }

    @Override
    public byte getId() {
        return TAG_FLOAT;
    }

    @Override
    public @NotNull TagType<FloatTag> getType() {
        return TYPE;
    }

    @Override
    public @NotNull FloatTag copy() {
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
        return (long) value;
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
