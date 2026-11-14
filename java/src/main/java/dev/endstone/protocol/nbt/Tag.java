package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufUtils;
import dev.endstone.protocol.DecodeBudget;
import io.netty.buffer.ByteBuf;

/** A network NBT value; its payload is written without a type id or a name. */
public sealed interface Tag
        permits ByteTag,
                ShortTag,
                IntTag,
                Int64Tag,
                FloatTag,
                DoubleTag,
                StringTag,
                ByteArrayTag,
                IntArrayTag,
                ListTag,
                CompoundTag {
    TagType type();

    void encodeData(ByteBuf buf);

    /** Reads the payload of a tag of the given type; END has none. */
    static Tag readData(ByteBuf buf, DecodeBudget budget, TagType type) {
        budget.enter(buf.readerIndex());
        try {
            return switch (type) {
                case BYTE -> new ByteTag(ByteBufUtils.readUnsignedByte(buf));
                case SHORT -> new ShortTag(ByteBufUtils.readShortLE(buf));
                case INT -> new IntTag(ByteBufUtils.readVarInt(buf));
                case INT64 -> new Int64Tag(ByteBufUtils.readVarLong(buf));
                case FLOAT -> new FloatTag(ByteBufUtils.readFloatLE(buf));
                case DOUBLE -> new DoubleTag(ByteBufUtils.readDoubleLE(buf));
                case STRING -> new StringTag(ByteBufUtils.readString(buf, budget));
                case BYTE_ARRAY -> ByteArrayTag.readBody(buf, budget);
                case INT_ARRAY -> IntArrayTag.readBody(buf, budget);
                case LIST -> ListTag.readBody(buf, budget);
                case COMPOUND -> CompoundTag.readBody(buf, budget);
                case END -> throw new IllegalArgumentException("Tag.readData: END has no payload");
            };
        } finally {
            budget.leave();
        }
    }
}
