package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

final class ProtocolVersionTest {
    @Test
    void aNumberAfterASnapshotSharesItsSnapshot() {
        assertEquals(2168, ProtocolVersion.of(2169).orElseThrow().snapshot());
    }

    @Test
    void aReleaseInsideARangeFindsTheRange() {
        assertEquals(2225, ProtocolVersion.of("1.26.63").orElseThrow().number());
    }

    @Test
    void anUnknownNumberIsEmpty() {
        assertTrue(ProtocolVersion.of(1).isEmpty());
    }

    @Test
    void aMalformedReleaseIsEmpty() {
        assertTrue(ProtocolVersion.of("1.26").isEmpty());
    }
}
