package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufCodec;
import dev.endstone.protocol.DecodeException;
import dev.endstone.protocol.DecodeException.Reason;
import io.netty.buffer.ByteBuf;
import java.util.AbstractList;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import org.jetbrains.annotations.NotNull;

/** A list tag; every element has the element type, and an empty list may name any type. */
public final class ListTag extends AbstractList<Tag> implements CollectionTag {
    public static final @NotNull TagType<ListTag> TYPE =
            buf -> {
                int id = ByteBufCodec.readUnsignedByte(buf);
                long count = ByteBufCodec.readVarint32Count(buf);
                TagType<?> elementType = TagTypes.getType(id);
                if (elementType == null || (count > 0 && id == TAG_END)) {
                    throw new DecodeException(Reason.UNKNOWN_VALUE, buf.readerIndex());
                }
                int size = ByteBufCodec.toCount(buf, count);
                List<Tag> elements = new ArrayList<>(ByteBufCodec.initialCapacity(size));
                for (int i = 0; i < size; i++) {
                    elements.add(elementType.deserialize(buf));
                }
                return new ListTag((byte) id, elements);
            };

    private final List<Tag> list = new ArrayList<>();
    private byte elementType;

    public ListTag() {}

    public ListTag(@NotNull List<Tag> elements) {
        addAll(elements);
    }

    public ListTag(byte elementType, @NotNull List<Tag> elements) {
        this.elementType = elementType;
        addAll(elements);
    }

    public byte getElementType() {
        return elementType;
    }

    @Override
    public void serialize(@NotNull ByteBuf buf) {
        buf.writeByte(elementType);
        ByteBufCodec.writeVarInt(buf, list.size());
        for (Tag element : list) {
            element.serialize(buf);
        }
    }

    @Override
    public byte getId() {
        return TAG_LIST;
    }

    @Override
    public @NotNull TagType<ListTag> getType() {
        return TYPE;
    }

    @Override
    public @NotNull ListTag copy() {
        List<Tag> copies = new ArrayList<>(list.size());
        for (Tag element : list) {
            copies.add(element.copy());
        }
        return new ListTag(elementType, copies);
    }

    @Override
    public int size() {
        return list.size();
    }

    @Override
    public @NotNull Tag get(int index) {
        return list.get(index);
    }

    @Override
    public @NotNull Tag set(int index, @NotNull Tag element) {
        requireElementType(element);
        return list.set(index, element);
    }

    @Override
    public void add(int index, @NotNull Tag element) {
        requireElementType(element);
        list.add(index, element);
    }

    @Override
    public @NotNull Tag remove(int index) {
        return list.remove(index);
    }

    @Override
    public @NotNull Optional<ListTag> asList() {
        return Optional.of(this);
    }

    public @NotNull Optional<CompoundTag> getCompound(int index) {
        return getOptional(index).flatMap(Tag::asCompound);
    }

    public @NotNull CompoundTag getCompoundOrEmpty(int index) {
        return getCompound(index).orElseGet(CompoundTag::new);
    }

    public @NotNull Optional<ListTag> getList(int index) {
        return getOptional(index).flatMap(Tag::asList);
    }

    public @NotNull ListTag getListOrEmpty(int index) {
        return getList(index).orElseGet(ListTag::new);
    }

    public @NotNull Optional<Short> getShort(int index) {
        return getOptional(index).flatMap(Tag::asShort);
    }

    public short getShortOr(int index, short fallback) {
        return getShort(index).orElse(fallback);
    }

    public @NotNull Optional<Integer> getInt(int index) {
        return getOptional(index).flatMap(Tag::asInt);
    }

    public int getIntOr(int index, int fallback) {
        return getInt(index).orElse(fallback);
    }

    public @NotNull Optional<int[]> getIntArray(int index) {
        return getOptional(index).flatMap(Tag::asIntArray);
    }

    public @NotNull Optional<Double> getDouble(int index) {
        return getOptional(index).flatMap(Tag::asDouble);
    }

    public double getDoubleOr(int index, double fallback) {
        return getDouble(index).orElse(fallback);
    }

    public @NotNull Optional<Float> getFloat(int index) {
        return getOptional(index).flatMap(Tag::asFloat);
    }

    public float getFloatOr(int index, float fallback) {
        return getFloat(index).orElse(fallback);
    }

    public @NotNull Optional<String> getString(int index) {
        return getOptional(index).flatMap(Tag::asString);
    }

    public @NotNull String getStringOr(int index, @NotNull String fallback) {
        return getString(index).orElse(fallback);
    }

    private Optional<Tag> getOptional(int index) {
        return index >= 0 && index < list.size() ? Optional.of(list.get(index)) : Optional.empty();
    }

    private void requireElementType(Tag element) {
        Objects.requireNonNull(element, "ListTag.element");
        if (element.getId() == TAG_END) {
            throw new IllegalArgumentException("ListTag.element: END in a list");
        }
        if (elementType == TAG_END) {
            elementType = element.getId();
        } else if (element.getId() != elementType) {
            throw new IllegalArgumentException(
                    "ListTag.element: tag " + element.getId() + " in a list of tag " + elementType);
        }
    }
}
