package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufCodec;
import dev.endstone.protocol.DecodeException;
import io.netty.buffer.ByteBuf;
import java.util.Arrays;
import java.util.Objects;
import java.util.Optional;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

/** An int array tag; two compare equal when their ints do. */
public final class IntArrayTag implements CollectionTag {
  public static final @NotNull TagType<IntArrayTag> TYPE =
      buf -> {
        int count = ByteBufCodec.toCount(buf, ByteBufCodec.readVarint32Count(buf));
        if (count > buf.readableBytes()) {
          throw DecodeException.truncated(buf.readerIndex());
        }
        int[] data = new int[count];
        for (int i = 0; i < count; i++) {
          data[i] = ByteBufCodec.readVarInt(buf);
        }
        return new IntArrayTag(data);
      };

  private final int @NotNull [] data;

  public IntArrayTag(int @NotNull [] data) {
    this.data = Objects.requireNonNull(data, "IntArrayTag.data");
  }

  @Override
  public void encode(@NotNull ByteBuf buf) {
    ByteBufCodec.writeVarInt(buf, data.length);
    for (int element : data) {
      ByteBufCodec.writeVarInt(buf, element);
    }
  }

  @Override
  public byte getId() {
    return TAG_INT_ARRAY;
  }

  @Override
  public @NotNull TagType<IntArrayTag> getType() {
    return TYPE;
  }

  @Override
  public @NotNull IntArrayTag copy() {
    return new IntArrayTag(data.clone());
  }

  public int @NotNull [] getAsIntArray() {
    return data;
  }

  @Override
  public int size() {
    return data.length;
  }

  @Override
  public @NotNull IntTag get(int index) {
    return IntTag.valueOf(data[index]);
  }

  @Override
  public @NotNull Optional<int[]> asIntArray() {
    return Optional.of(data);
  }

  @Override
  public boolean equals(@Nullable Object other) {
    return other instanceof IntArrayTag tag && Arrays.equals(data, tag.data);
  }

  @Override
  public int hashCode() {
    return Arrays.hashCode(data);
  }

  @Override
  public @NotNull String toString() {
    return "IntArrayTag" + Arrays.toString(data);
  }
}
