package dev.endstone.protocol;

/** The most a single decode may allocate and nest. */
public record DecodeLimits(int maxElements, long maxBytes, int maxDepth) {
    public static final DecodeLimits DEFAULT = new DecodeLimits(1_048_576, 64L * 1024 * 1024, 128);

    public DecodeLimits {
        if (maxElements < 0 || maxBytes < 0 || maxDepth < 0) {
            throw new IllegalArgumentException("decode limits cannot be negative");
        }
    }
}
