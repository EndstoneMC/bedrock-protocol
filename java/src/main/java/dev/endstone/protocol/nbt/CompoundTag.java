package dev.endstone.protocol.nbt;

import dev.endstone.protocol.DecodeBudget;
import dev.endstone.protocol.DecodeException;
import dev.endstone.protocol.DecodeException.Reason;
import dev.endstone.protocol.Wire;
import io.netty.buffer.ByteBuf;
import java.util.Collections;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;

/** A compound tag; its entries are kept, and written, in the unsigned byte order of their keys. */
public record CompoundTag(Map<String, Tag> entries) implements Tag {
    public CompoundTag {
        TreeMap<String, Tag> sorted = new TreeMap<>(Wire.STR_ORDER);
        for (Map.Entry<String, Tag> entry : entries.entrySet()) {
            sorted.put(
                    Objects.requireNonNull(entry.getKey(), "CompoundTag.entries key"),
                    Objects.requireNonNull(entry.getValue(), "CompoundTag.entries value"));
        }
        entries = Collections.unmodifiableMap(sorted);
    }

    @Override
    public TagType type() {
        return TagType.COMPOUND;
    }

    /** Writes the tag as a root: its type id, an empty name, then the payload. */
    public void encode(ByteBuf buf) {
        buf.writeByte(TagType.COMPOUND.getNumber());
        Wire.writeStr(buf, "");
        encodeData(buf);
    }

    @Override
    public void encodeData(ByteBuf buf) {
        for (Map.Entry<String, Tag> entry : entries.entrySet()) {
            buf.writeByte(entry.getValue().type().getNumber());
            Wire.writeStr(buf, entry.getKey());
            entry.getValue().encodeData(buf);
        }
        buf.writeByte(TagType.END.getNumber());
    }

    /** Reads a root: its type id, its name, which is dropped, then the payload. */
    public static CompoundTag read(ByteBuf buf, DecodeBudget budget) {
        TagType type = TagType.forNumber(Wire.readUint8(buf));
        if (type == null || type == TagType.END) {
            throw new DecodeException(Reason.UNKNOWN_VALUE, buf.readerIndex());
        }
        Wire.readStr(buf, budget);
        if (!(Tag.readData(buf, budget, type) instanceof CompoundTag tag)) {
            throw new DecodeException(Reason.UNKNOWN_VALUE, buf.readerIndex());
        }
        return tag;
    }

    /** Reads a payload. */
    public static CompoundTag readData(ByteBuf buf, DecodeBudget budget) {
        return (CompoundTag) Tag.readData(buf, budget, TagType.COMPOUND);
    }

    /** Reads entries up to the END id; a repeated key keeps its first value. */
    static CompoundTag readEntries(ByteBuf buf, DecodeBudget budget) {
        TreeMap<String, Tag> entries = new TreeMap<>(Wire.STR_ORDER);
        for (; ; ) {
            int number = Wire.readUint8(buf);
            if (number == TagType.END.getNumber()) {
                return new CompoundTag(entries);
            }
            TagType type = TagType.forNumber(number);
            if (type == null) {
                throw new DecodeException(Reason.UNKNOWN_VALUE, buf.readerIndex());
            }
            budget.chargeElements(1, buf.readerIndex());
            String name = Wire.readStr(buf, budget);
            entries.putIfAbsent(name, Tag.readData(buf, budget, type));
        }
    }
}
