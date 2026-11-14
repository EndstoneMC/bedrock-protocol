package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufCodec;
import dev.endstone.protocol.DecodeException;
import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

/** Encodes and decodes a root compound in the network encoding: type id, empty name, payload. */
public final class NbtIo {
    private NbtIo() {}

    public static void encode(@NotNull CompoundTag tag, @NotNull ByteBuf buf) {
        buf.writeByte(Tag.TAG_COMPOUND);
        ByteBufCodec.writeString(buf, "");
        tag.encode(buf);
    }

    /** Decodes a root and drops its name. */
    public static @NotNull CompoundTag decode(@NotNull ByteBuf buf) {
        int id = ByteBufCodec.readUnsignedByte(buf);
        TagType<?> type = TagTypes.getType(id);
        if (type == null || id == Tag.TAG_END) {
            throw DecodeException.unknownValue(buf.readerIndex());
        }
        ByteBufCodec.readString(buf);
        if (!(type.decode(buf) instanceof CompoundTag tag)) {
            throw DecodeException.unknownValue(buf.readerIndex());
        }
        return tag;
    }
}
