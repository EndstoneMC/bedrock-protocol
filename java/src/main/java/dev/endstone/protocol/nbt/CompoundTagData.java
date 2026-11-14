package dev.endstone.protocol.nbt;

import java.util.Objects;
import org.jetbrains.annotations.NotNull;

/** A compound tag in its payload form: the entries and the end marker, with no root id or name. */
public record CompoundTagData(@NotNull CompoundTag tag) {
    public CompoundTagData {
        Objects.requireNonNull(tag, "CompoundTagData.tag");
    }

    public static @NotNull CompoundTagData getDefaultInstance() {
        return new CompoundTagData(new CompoundTag());
    }

    public @NotNull CompoundTagData copy() {
        return new CompoundTagData(tag.copy());
    }
}
