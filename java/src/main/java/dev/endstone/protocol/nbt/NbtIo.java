package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufCodec;
import dev.endstone.protocol.DecodeException;
import dev.endstone.protocol.DecodeException.Reason;
import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

/**
 * Serializes and deserializes a root compound in the network encoding: type id, empty name,
 * payload.
 */
public final class NbtIo {
    private NbtIo() {}

    public static void serialize(@NotNull CompoundTag tag, @NotNull ByteBuf buf) {
        buf.writeByte(Tag.TAG_COMPOUND);
        ByteBufCodec.writeString(buf, "");
        tag.serialize(buf);
    }

    /** Deserializes a root and drops its name. */
    public static @NotNull CompoundTag deserialize(@NotNull ByteBuf buf) {
        int id = ByteBufCodec.readUnsignedByte(buf);
        TagType<?> type = TagTypes.getType(id);
        if (type == null || id == Tag.TAG_END) {
            throw new DecodeException(Reason.UNKNOWN_VALUE, buf.readerIndex());
        }
        ByteBufCodec.readString(buf);
        if (!(type.deserialize(buf) instanceof CompoundTag tag)) {
            throw new DecodeException(Reason.UNKNOWN_VALUE, buf.readerIndex());
        }
        return tag;
    }
}
