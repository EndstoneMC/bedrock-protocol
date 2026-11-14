package dev.endstone.protocol.nbt;

import dev.endstone.protocol.ByteBufCodec;
import dev.endstone.protocol.DecodeException;
import dev.endstone.protocol.DecodeException.Reason;
import io.netty.buffer.ByteBuf;
import java.util.Collection;
import java.util.Collections;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;
import java.util.function.BiConsumer;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

/** A compound tag; its entries are kept, and encoded, in the unsigned byte order of their keys. */
public final class CompoundTag implements Tag {
    public static final @NotNull TagType<CompoundTag> TYPE =
            buf -> {
                CompoundTag tag = new CompoundTag();
                while (true) {
                    int id = ByteBufCodec.readUnsignedByte(buf);
                    if (id == TAG_END) {
                        return tag;
                    }
                    TagType<?> type = TagTypes.getType(id);
                    if (type == null) {
                        throw new DecodeException(Reason.UNKNOWN_VALUE, buf.readerIndex());
                    }
                    String name = ByteBufCodec.readString(buf);
                    tag.tags.putIfAbsent(name, type.decode(buf));
                }
            };

    private final Map<String, Tag> tags = new TreeMap<>(ByteBufCodec.STR_ORDER);

    @Override
    public void encode(@NotNull ByteBuf buf) {
        for (Map.Entry<String, Tag> entry : tags.entrySet()) {
            buf.writeByte(entry.getValue().getId());
            ByteBufCodec.writeString(buf, entry.getKey());
            entry.getValue().encode(buf);
        }
        buf.writeByte(TAG_END);
    }

    @Override
    public byte getId() {
        return TAG_COMPOUND;
    }

    @Override
    public @NotNull TagType<CompoundTag> getType() {
        return TYPE;
    }

    @Override
    public @NotNull CompoundTag copy() {
        CompoundTag copy = new CompoundTag();
        tags.forEach((key, value) -> copy.tags.put(key, value.copy()));
        return copy;
    }

    @Override
    public @NotNull Optional<CompoundTag> asCompound() {
        return Optional.of(this);
    }

    public int size() {
        return tags.size();
    }

    public boolean isEmpty() {
        return tags.isEmpty();
    }

    public @NotNull Set<String> keySet() {
        return Collections.unmodifiableSet(tags.keySet());
    }

    public @NotNull Set<Map.Entry<String, Tag>> entrySet() {
        return Collections.unmodifiableMap(tags).entrySet();
    }

    public @NotNull Collection<Tag> values() {
        return Collections.unmodifiableCollection(tags.values());
    }

    public void forEach(@NotNull BiConsumer<String, Tag> action) {
        tags.forEach(action);
    }

    public @Nullable Tag put(@NotNull String key, @NotNull Tag value) {
        return tags.put(
                Objects.requireNonNull(key, "CompoundTag.key"),
                Objects.requireNonNull(value, "CompoundTag.value"));
    }

    public void putByte(@NotNull String key, byte value) {
        put(key, ByteTag.valueOf(value));
    }

    public void putShort(@NotNull String key, short value) {
        put(key, ShortTag.valueOf(value));
    }

    public void putInt(@NotNull String key, int value) {
        put(key, IntTag.valueOf(value));
    }

    public void putLong(@NotNull String key, long value) {
        put(key, LongTag.valueOf(value));
    }

    public void putFloat(@NotNull String key, float value) {
        put(key, FloatTag.valueOf(value));
    }

    public void putDouble(@NotNull String key, double value) {
        put(key, DoubleTag.valueOf(value));
    }

    public void putString(@NotNull String key, @NotNull String value) {
        put(key, StringTag.valueOf(value));
    }

    public void putByteArray(@NotNull String key, byte @NotNull [] value) {
        put(key, new ByteArrayTag(value));
    }

    public void putIntArray(@NotNull String key, int @NotNull [] value) {
        put(key, new IntArrayTag(value));
    }

    public void putBoolean(@NotNull String key, boolean value) {
        put(key, ByteTag.valueOf(value));
    }

    public @Nullable Tag get(@NotNull String key) {
        return tags.get(key);
    }

    public boolean contains(@NotNull String key) {
        return tags.containsKey(key);
    }

    public @Nullable Tag remove(@NotNull String key) {
        return tags.remove(key);
    }

    public @NotNull Optional<Byte> getByte(@NotNull String key) {
        return getOptional(key).flatMap(Tag::asByte);
    }

    public byte getByteOr(@NotNull String key, byte fallback) {
        return getByte(key).orElse(fallback);
    }

    public @NotNull Optional<Short> getShort(@NotNull String key) {
        return getOptional(key).flatMap(Tag::asShort);
    }

    public short getShortOr(@NotNull String key, short fallback) {
        return getShort(key).orElse(fallback);
    }

    public @NotNull Optional<Integer> getInt(@NotNull String key) {
        return getOptional(key).flatMap(Tag::asInt);
    }

    public int getIntOr(@NotNull String key, int fallback) {
        return getInt(key).orElse(fallback);
    }

    public @NotNull Optional<Long> getLong(@NotNull String key) {
        return getOptional(key).flatMap(Tag::asLong);
    }

    public long getLongOr(@NotNull String key, long fallback) {
        return getLong(key).orElse(fallback);
    }

    public @NotNull Optional<Float> getFloat(@NotNull String key) {
        return getOptional(key).flatMap(Tag::asFloat);
    }

    public float getFloatOr(@NotNull String key, float fallback) {
        return getFloat(key).orElse(fallback);
    }

    public @NotNull Optional<Double> getDouble(@NotNull String key) {
        return getOptional(key).flatMap(Tag::asDouble);
    }

    public double getDoubleOr(@NotNull String key, double fallback) {
        return getDouble(key).orElse(fallback);
    }

    public @NotNull Optional<String> getString(@NotNull String key) {
        return getOptional(key).flatMap(Tag::asString);
    }

    public @NotNull String getStringOr(@NotNull String key, @NotNull String fallback) {
        return getString(key).orElse(fallback);
    }

    public @NotNull Optional<byte[]> getByteArray(@NotNull String key) {
        return getOptional(key).flatMap(Tag::asByteArray);
    }

    public @NotNull Optional<int[]> getIntArray(@NotNull String key) {
        return getOptional(key).flatMap(Tag::asIntArray);
    }

    public @NotNull Optional<CompoundTag> getCompound(@NotNull String key) {
        return getOptional(key).flatMap(Tag::asCompound);
    }

    public @NotNull CompoundTag getCompoundOrEmpty(@NotNull String key) {
        return getCompound(key).orElseGet(CompoundTag::new);
    }

    public @NotNull Optional<ListTag> getList(@NotNull String key) {
        return getOptional(key).flatMap(Tag::asList);
    }

    public @NotNull ListTag getListOrEmpty(@NotNull String key) {
        return getList(key).orElseGet(ListTag::new);
    }

    public @NotNull Optional<Boolean> getBoolean(@NotNull String key) {
        return getOptional(key).flatMap(Tag::asBoolean);
    }

    public boolean getBooleanOr(@NotNull String key, boolean fallback) {
        return getBoolean(key).orElse(fallback);
    }

    private Optional<Tag> getOptional(String key) {
        return Optional.ofNullable(tags.get(key));
    }

    @Override
    public boolean equals(@Nullable Object other) {
        return other instanceof CompoundTag tag && tags.equals(tag.tags);
    }

    @Override
    public int hashCode() {
        return tags.hashCode();
    }

    @Override
    public @NotNull String toString() {
        return "CompoundTag" + tags;
    }
}
