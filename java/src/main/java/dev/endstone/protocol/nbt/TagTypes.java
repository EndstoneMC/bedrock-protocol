package dev.endstone.protocol.nbt;

import org.jetbrains.annotations.Nullable;

public final class TagTypes {
    private static final TagType<?>[] TYPES = {
        EndTag.TYPE,
        ByteTag.TYPE,
        ShortTag.TYPE,
        IntTag.TYPE,
        LongTag.TYPE,
        FloatTag.TYPE,
        DoubleTag.TYPE,
        ByteArrayTag.TYPE,
        StringTag.TYPE,
        ListTag.TYPE,
        CompoundTag.TYPE,
        IntArrayTag.TYPE
    };

    private TagTypes() {}

    /** Returns the type with this id, or null when there is none. */
    public static @Nullable TagType<?> getType(int id) {
        return id >= 0 && id < TYPES.length ? TYPES[id] : null;
    }
}
