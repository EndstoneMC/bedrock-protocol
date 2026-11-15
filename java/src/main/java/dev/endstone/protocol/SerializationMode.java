package dev.endstone.protocol;

/** Picks a type's encoding where a protocol sends it both cereal and hand-written, else DEFAULT. */
public enum SerializationMode {
    DEFAULT,
    CEREAL,
    MANUAL
}
