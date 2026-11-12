package dev.endstone.protocol;

import java.io.Serial;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Bad bytes from a peer; catch it where a packet enters. */
public final class DecodeException extends RuntimeException {
    /** Why a decode failed, in the order of the C++ error codes. */
    public enum Reason {
        TRUNCATED("truncated"),
        OUT_OF_RANGE("out of range"),
        UNKNOWN_VALUE("unknown value"),
        TOO_LARGE("too large"),
        TOO_DEEP("too deep"),
        TRAILING_BYTES("trailing bytes");

        private final String text;

        Reason(String text) {
            this.text = text;
        }

        String text() {
            return text;
        }
    }

    @Serial private static final long serialVersionUID = 1L;

    private final Reason reason;
    private final ArrayList<Object> path = new ArrayList<>();
    private String type = "";
    private int offset;
    private int length;

    public DecodeException(Reason reason, int offset) {
        this.reason = reason;
        this.offset = offset;
    }

    /** Puts a field name in front of the path. */
    public DecodeException prepend(String field) {
        path.addFirst(field);
        return this;
    }

    /** Puts a list index in front of the path. */
    public DecodeException prepend(int index) {
        path.addFirst(index);
        return this;
    }

    void stamp(String type, int offset, int length) {
        this.type = type;
        this.offset = offset;
        this.length = length;
    }

    public Reason getReason() {
        return reason;
    }

    public String getType() {
        return type;
    }

    /** The field names (String) and list indices (Integer), outermost first. */
    public List<Object> getPath() {
        return Collections.unmodifiableList(path);
    }

    /** Bytes from the first byte decode was handed. */
    public int getOffset() {
        return offset;
    }

    /** Bytes decode was handed. */
    public int getLength() {
        return length;
    }

    @Override
    public String getMessage() {
        StringBuilder message = new StringBuilder(type);
        for (Object segment : path) {
            if (segment instanceof Integer index) {
                message.append('[').append(index).append(']');
            } else {
                message.append('.').append(segment);
            }
        }
        return message.append(": ")
                .append(reason.text())
                .append(" at byte ")
                .append(offset)
                .append(" of ")
                .append(length)
                .toString();
    }
}
