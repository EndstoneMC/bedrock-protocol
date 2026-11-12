package dev.endstone.protocol;

import dev.endstone.protocol.DecodeException.Reason;

/** The running totals of one decode; not thread-safe. */
public final class DecodeBudget {
    private final DecodeLimits limits;
    private long elements;
    private long bytes;
    private int depth;

    public DecodeBudget(DecodeLimits limits) {
        this.limits = limits;
    }

    /** Charges count elements, or throws OUT_OF_RANGE or TOO_LARGE at the given byte offset. */
    public void chargeElements(long count, int offset) {
        if (count < 0) {
            throw new DecodeException(Reason.OUT_OF_RANGE, offset);
        }
        if (count > limits.maxElements() - elements) {
            throw new DecodeException(Reason.TOO_LARGE, offset);
        }
        elements += count;
    }

    /** Charges count bytes, or throws OUT_OF_RANGE or TOO_LARGE at the given byte offset. */
    public void chargeBytes(long count, int offset) {
        if (count < 0) {
            throw new DecodeException(Reason.OUT_OF_RANGE, offset);
        }
        if (count > limits.maxBytes() - bytes) {
            throw new DecodeException(Reason.TOO_LARGE, offset);
        }
        bytes += count;
    }

    /** Descends one level, or throws TOO_DEEP at the given byte offset. */
    public void enter(int offset) {
        if (depth >= limits.maxDepth()) {
            throw new DecodeException(Reason.TOO_DEEP, offset);
        }
        depth++;
    }

    public void leave() {
        depth--;
    }
}
