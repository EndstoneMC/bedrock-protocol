package dev.endstone.protocol.nbt;

import io.netty.buffer.ByteBuf;
import java.util.Optional;
import org.jetbrains.annotations.NotNull;

/** A network NBT value; its payload is encoded without a type id or a name. */
public sealed interface Tag permits CollectionTag, CompoundTag, EndTag, PrimitiveTag {
    byte TAG_END = 0;
    byte TAG_BYTE = 1;
    byte TAG_SHORT = 2;
    byte TAG_INT = 3;
    byte TAG_LONG = 4;
    byte TAG_FLOAT = 5;
    byte TAG_DOUBLE = 6;
    byte TAG_BYTE_ARRAY = 7;
    byte TAG_STRING = 8;
    byte TAG_LIST = 9;
    byte TAG_COMPOUND = 10;
    byte TAG_INT_ARRAY = 11;

    void encode(@NotNull ByteBuf buf);

    byte getId();

    @NotNull
    TagType<?> getType();

    @NotNull
    Tag copy();

    default @NotNull Optional<String> asString() {
        return Optional.empty();
    }

    default @NotNull Optional<Number> asNumber() {
        return Optional.empty();
    }

    default @NotNull Optional<Byte> asByte() {
        return Optional.empty();
    }

    default @NotNull Optional<Short> asShort() {
        return Optional.empty();
    }

    default @NotNull Optional<Integer> asInt() {
        return Optional.empty();
    }

    default @NotNull Optional<Long> asLong() {
        return Optional.empty();
    }

    default @NotNull Optional<Float> asFloat() {
        return Optional.empty();
    }

    default @NotNull Optional<Double> asDouble() {
        return Optional.empty();
    }

    default @NotNull Optional<Boolean> asBoolean() {
        return Optional.empty();
    }

    default @NotNull Optional<byte[]> asByteArray() {
        return Optional.empty();
    }

    default @NotNull Optional<int[]> asIntArray() {
        return Optional.empty();
    }

    default @NotNull Optional<CompoundTag> asCompound() {
        return Optional.empty();
    }

    default @NotNull Optional<ListTag> asList() {
        return Optional.empty();
    }
}
