package dev.endstone.protocol.nbt;

import dev.endstone.protocol.DecodeBudget;
import dev.endstone.protocol.DecodeException;
import dev.endstone.protocol.DecodeException.Reason;
import dev.endstone.protocol.Wire;
import io.netty.buffer.ByteBuf;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/** A list tag; every element has the element type, and an empty list may name any type. */
public record ListTag(TagType elementType, List<Tag> elements) implements Tag {
    public ListTag {
        Objects.requireNonNull(elementType, "ListTag.elementType");
        elements = List.copyOf(elements);
        for (Tag element : elements) {
            if (element.type() != elementType) {
                throw new IllegalArgumentException(
                        "ListTag.elements: " + element.type() + " in a list of " + elementType);
            }
        }
    }

    @Override
    public TagType type() {
        return TagType.LIST;
    }

    @Override
    public void encodeData(ByteBuf buf) {
        buf.writeByte(elementType.getNumber());
        Wire.writeVarint32(buf, elements.size());
        for (Tag element : elements) {
            element.encodeData(buf);
        }
    }

    static ListTag readBody(ByteBuf buf, DecodeBudget budget) {
        int number = Wire.readUint8(buf);
        long count = Wire.readVarint32Count(buf);
        TagType elementType = TagType.forNumber(number);
        if (elementType == null || (count > 0 && elementType == TagType.END)) {
            throw new DecodeException(Reason.UNKNOWN_VALUE, buf.readerIndex());
        }
        int size = Wire.charge(buf, budget, count, 0);
        List<Tag> elements = new ArrayList<>(Wire.initialCapacity(size));
        for (int i = 0; i < size; i++) {
            elements.add(Tag.readData(buf, budget, elementType));
        }
        return new ListTag(elementType, elements);
    }
}
