package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufCodec;
import dev.endstone.protocol.DecodeException;
import dev.endstone.protocol.DecodeException.Reason;
import io.netty.buffer.ByteBuf;
import java.util.Arrays;
import java.util.Objects;
import java.util.Optional;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

/** A byte array tag; two compare equal when their bytes do. */
public final class ByteArrayTag implements CollectionTag {
    public static final @NotNull TagType<ByteArrayTag> TYPE =
            buf -> {
                int count = ByteBufCodec.toCount(buf, ByteBufCodec.readVarint32Count(buf));
                if (count > buf.readableBytes()) {
                    throw new DecodeException(Reason.TRUNCATED, buf.readerIndex());
                }
                byte[] data = new byte[count];
                buf.readBytes(data);
                return new ByteArrayTag(data);
            };

    private final byte @NotNull [] data;

    public ByteArrayTag(byte @NotNull [] data) {
        this.data = Objects.requireNonNull(data, "ByteArrayTag.data");
    }

    @Override
    public void encode(@NotNull ByteBuf buf) {
        ByteBufCodec.writeVarInt(buf, data.length);
        buf.writeBytes(data);
    }

    @Override
    public byte getId() {
        return TAG_BYTE_ARRAY;
    }

    @Override
    public @NotNull TagType<ByteArrayTag> getType() {
        return TYPE;
    }

    @Override
    public @NotNull ByteArrayTag copy() {
        return new ByteArrayTag(data.clone());
    }

    public byte @NotNull [] getAsByteArray() {
        return data;
    }

    @Override
    public int size() {
        return data.length;
    }

    @Override
    public @NotNull ByteTag get(int index) {
        return ByteTag.valueOf(data[index]);
    }

    @Override
    public @NotNull Optional<byte[]> asByteArray() {
        return Optional.of(data);
    }

    @Override
    public boolean equals(@Nullable Object other) {
        return other instanceof ByteArrayTag tag && Arrays.equals(data, tag.data);
    }

    @Override
    public int hashCode() {
        return Arrays.hashCode(data);
    }

    @Override
    public @NotNull String toString() {
        return "ByteArrayTag" + Arrays.toString(data);
    }
}
