package dev.endstone.protocol.nbt;

import dev.endstone.protocol.DecodeBudget;
import dev.endstone.protocol.Wire;
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
                case BYTE -> new ByteTag(Wire.readInt8(buf));
                case SHORT -> new ShortTag(Wire.readInt16(buf));
                case INT -> new IntTag(Wire.readVarint32(buf));
                case INT64 -> new Int64Tag(Wire.readVarint64(buf));
                case FLOAT -> new FloatTag(Wire.readFloat(buf));
                case DOUBLE -> new DoubleTag(Wire.readDouble(buf));
                case STRING -> new StringTag(Wire.readStr(buf, budget));
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
