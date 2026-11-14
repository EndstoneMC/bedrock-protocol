package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufCodec;
import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

public record ByteTag(byte value) implements NumericTag {
    public static final @NotNull TagType<ByteTag> TYPE = buf -> valueOf(ByteBufCodec.readByte(buf));

    public static final @NotNull ByteTag ZERO = valueOf((byte) 0);
    public static final @NotNull ByteTag ONE = valueOf((byte) 1);

    public static @NotNull ByteTag valueOf(byte value) {
        return new ByteTag(value);
    }

    public static @NotNull ByteTag valueOf(boolean value) {
        return value ? ONE : ZERO;
    }

    @Override
    public void serialize(@NotNull ByteBuf buf) {
        buf.writeByte(value);
    }

    @Override
    public byte getId() {
        return TAG_BYTE;
    }

    @Override
    public @NotNull TagType<ByteTag> getType() {
        return TYPE;
    }

    @Override
    public @NotNull ByteTag copy() {
        return this;
    }

    @Override
    public byte byteValue() {
        return value;
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
