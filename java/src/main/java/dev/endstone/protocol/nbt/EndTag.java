package dev.endstone.protocol.nbt;

import io.netty.buffer.ByteBuf;
import org.jetbrains.annotations.NotNull;

public final class EndTag implements Tag {
    public static final @NotNull TagType<EndTag> TYPE = buf -> EndTag.INSTANCE;
    public static final @NotNull EndTag INSTANCE = new EndTag();

    private EndTag() {}

    @Override
    public void serialize(@NotNull ByteBuf buf) {}

    @Override
    public byte getId() {
        return TAG_END;
    }

    @Override
    public @NotNull TagType<EndTag> getType() {
        return TYPE;
    }

    @Override
    public @NotNull EndTag copy() {
        return this;
    }

    @Override
    public @NotNull String toString() {
        return "EndTag";
    }
}
