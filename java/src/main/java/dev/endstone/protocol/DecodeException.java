package dev.endstone.protocol;

import java.io.Serial;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

/** Bad bytes from a peer; catch it where a packet enters. */
public final class DecodeException extends RuntimeException {
    @Serial private static final long serialVersionUID = 1L;

    private final String reason;
    private final ArrayList<Object> path = new ArrayList<>();
    private String type = "";
    private int offset;
    private int start;
    private int length;
    private transient @Nullable Message unfinishedMessage;

    private DecodeException(String reason, int offset) {
        this.reason = reason;
        this.offset = offset;
    }

    public static @NotNull DecodeException truncated(int offset) {
        return new DecodeException("truncated", offset);
    }

    public static @NotNull DecodeException outOfRange(int offset) {
        return new DecodeException("out of range", offset);
    }

    public static @NotNull DecodeException unknownValue(int offset) {
        return new DecodeException("unknown value", offset);
    }

    public static @NotNull DecodeException trailingBytes(int offset) {
        return new DecodeException("trailing bytes", offset);
    }

    /** Puts a field name in front of the path. */
    public @NotNull DecodeException prepend(@NotNull String field) {
        path.addFirst(field);
        return this;
    }

    /** Puts a list index in front of the path. */
    public @NotNull DecodeException prepend(int index) {
        path.addFirst(index);
        return this;
    }

    /** Replaces the message decoded up to the failing field. */
    public @NotNull DecodeException setUnfinishedMessage(@NotNull Message message) {
        this.unfinishedMessage = message;
        return this;
    }

    void stamp(String type, int start, int length) {
        if (this.type.isEmpty()) {
            this.type = type;
        }
        this.start = start;
        this.length = length;
    }

    /** The message decoded up to the failing field, or null. */
    public @Nullable Message getUnfinishedMessage() {
        return unfinishedMessage;
    }

    public @NotNull String getType() {
        return type;
    }

    /** The field names (String) and list indices (Integer), outermost first. */
    public @NotNull List<Object> getPath() {
        return Collections.unmodifiableList(path);
    }

    /** Bytes from the first byte the outermost decode was handed. */
    public int getOffset() {
        return offset - start;
    }

    /** Bytes the outermost decode was handed. */
    public int getLength() {
        return length;
    }

    @Override
    public @NotNull String getMessage() {
        StringBuilder message = new StringBuilder(type);
        for (Object segment : path) {
            if (segment instanceof Integer index) {
                message.append('[').append(index).append(']');
            } else {
                message.append('.').append(segment);
            }
        }
        return message.append(": ")
                .append(reason)
                .append(" at byte ")
                .append(getOffset())
                .append(" of ")
                .append(length)
                .toString();
    }
}
