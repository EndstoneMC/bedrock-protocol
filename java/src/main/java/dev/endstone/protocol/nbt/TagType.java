package dev.endstone.protocol.nbt;

import org.jspecify.annotations.Nullable;

/** The tag ids of the wire. */
public enum TagType {
    END(0),
    BYTE(1),
    SHORT(2),
    INT(3),
    INT64(4),
    FLOAT(5),
    DOUBLE(6),
    BYTE_ARRAY(7),
    STRING(8),
    LIST(9),
    COMPOUND(10),
    INT_ARRAY(11);

    private static final TagType[] VALUES = values();

    private final int number;

    TagType(int number) {
        this.number = number;
    }

    public int getNumber() {
        return number;
    }

    /** Returns the type with this id, or null when there is none. */
    public static @Nullable TagType forNumber(int number) {
        return number >= 0 && number < VALUES.length ? VALUES[number] : null;
    }
}
