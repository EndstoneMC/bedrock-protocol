package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufCodec;
import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

public record IntTag(int value) implements NumericTag {
  public static final @NotNull TagType<IntTag> TYPE = buf -> valueOf(ByteBufCodec.readVarInt(buf));

  public static @NotNull IntTag valueOf(int value) {
    return new IntTag(value);
  }

  @Override
  public void encode(@NotNull ByteBuf buf) {
    ByteBufCodec.writeVarInt(buf, value);
  }

  @Override
  public byte getId() {
    return TAG_INT;
  }

  @Override
  public @NotNull TagType<IntTag> getType() {
    return TYPE;
  }

  @Override
  public @NotNull IntTag copy() {
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
