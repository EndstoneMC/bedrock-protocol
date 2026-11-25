package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufCodec;
import io.netty.buffer.ByteBuf;
import java.util.Objects;
import java.util.Optional;
import org.jetbrains.annotations.NotNull;

public record StringTag(@NotNull String value) implements PrimitiveTag {
  public static final @NotNull TagType<StringTag> TYPE =
      buf -> valueOf(ByteBufCodec.readString(buf));

  public StringTag {
    Objects.requireNonNull(value, "StringTag.value");
  }

  public static @NotNull StringTag valueOf(@NotNull String value) {
    return new StringTag(value);
  }

  @Override
  public void encode(@NotNull ByteBuf buf) {
    ByteBufCodec.writeString(buf, value);
  }

  @Override
  public byte getId() {
    return TAG_STRING;
  }

  @Override
  public @NotNull TagType<StringTag> getType() {
    return TYPE;
  }

  @Override
  public @NotNull StringTag copy() {
    return this;
  }

  @Override
  public @NotNull Optional<String> asString() {
    return Optional.of(value);
  }
}
