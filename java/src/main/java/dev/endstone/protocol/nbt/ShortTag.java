package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufCodec;
import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

public record ShortTag(short value) implements NumericTag {
    public static final @NotNull TagType<ShortTag> TYPE =
            buf -> valueOf(ByteBufCodec.readShortLE(buf));

    public static @NotNull ShortTag valueOf(short value) {
        return new ShortTag(value);
    }

    @Override
    public void encode(@NotNull ByteBuf buf) {
        buf.writeShortLE(value);
    }

    @Override
    public byte getId() {
        return TAG_SHORT;
    }

    @Override
    public @NotNull TagType<ShortTag> getType() {
        return TYPE;
    }

    @Override
    public @NotNull ShortTag copy() {
        return this;
    }

    @Override
    public byte byteValue() {
        return (byte) (value & 255);
    }

    @Override
    public short shortValue() {
        return value;
    }

    @Override
    public int intValue() {
        return value;
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
