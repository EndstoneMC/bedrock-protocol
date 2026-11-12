package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import dev.endstone.protocol.DecodeException.Reason;
import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

class DecodeBudgetTest {
    static Stream<Arguments> negativeLimits() {
        return Stream.of(
                argumentSet("elements", -1, 0L, 0),
                argumentSet("bytes", 0, -1L, 0),
                argumentSet("depth", 0, 0L, -1));
    }

    @Test
    void defaultLimitsMatchTheCppDefaults() {
        assertEquals(new DecodeLimits(1_048_576, 67_108_864L, 128), DecodeLimits.DEFAULT);
    }

    @ParameterizedTest
    @MethodSource("negativeLimits")
    void negativeLimitIsRejected(int elements, long bytes, int depth) {
        IllegalArgumentException error =
                assertThrows(
                        IllegalArgumentException.class,
                        () -> new DecodeLimits(elements, bytes, depth));
        assertEquals("decode limits cannot be negative", error.getMessage());
    }

    @Test
    void oneElementPastTheLimitIsTooLarge() {
        DecodeBudget budget = new DecodeBudget(new DecodeLimits(10, 100, 4));
        budget.chargeElements(10, 0);
        DecodeException error =
                assertThrows(DecodeException.class, () -> budget.chargeElements(1, 3));
        assertEquals(List.of(Reason.TOO_LARGE, 3), List.of(error.getReason(), error.getOffset()));
    }

    @Test
    void elementChargesAccumulate() {
        DecodeBudget budget = new DecodeBudget(new DecodeLimits(10, 100, 4));
        budget.chargeElements(6, 0);
        DecodeException error =
                assertThrows(DecodeException.class, () -> budget.chargeElements(5, 0));
        assertEquals(Reason.TOO_LARGE, error.getReason());
    }

    @Test
    void oneBytePastTheLimitIsTooLarge() {
        DecodeBudget budget = new DecodeBudget(new DecodeLimits(10, 100, 4));
        budget.chargeBytes(100, 0);
        DecodeException error = assertThrows(DecodeException.class, () -> budget.chargeBytes(1, 9));
        assertEquals(List.of(Reason.TOO_LARGE, 9), List.of(error.getReason(), error.getOffset()));
    }

    @Test
    void hugeChargeDoesNotOverflow() {
        DecodeBudget budget = new DecodeBudget(new DecodeLimits(10, 100, 4));
        budget.chargeBytes(1, 0);
        DecodeException error =
                assertThrows(DecodeException.class, () -> budget.chargeBytes(Long.MAX_VALUE, 0));
        assertEquals(Reason.TOO_LARGE, error.getReason());
    }

    @Test
    void negativeElementCountIsOutOfRange() {
        DecodeBudget budget = new DecodeBudget(new DecodeLimits(10, 100, 4));
        DecodeException error =
                assertThrows(DecodeException.class, () -> budget.chargeElements(-5, 2));
        assertEquals(
                List.of(Reason.OUT_OF_RANGE, 2), List.of(error.getReason(), error.getOffset()));
    }

    @Test
    void negativeByteCountIsOutOfRange() {
        DecodeBudget budget = new DecodeBudget(new DecodeLimits(10, 100, 4));
        DecodeException error =
                assertThrows(DecodeException.class, () -> budget.chargeBytes(-5, 2));
        assertEquals(
                List.of(Reason.OUT_OF_RANGE, 2), List.of(error.getReason(), error.getOffset()));
    }

    @Test
    void oneLevelPastTheLimitIsTooDeep() {
        DecodeBudget budget = new DecodeBudget(new DecodeLimits(10, 100, 2));
        budget.enter(0);
        budget.enter(0);
        DecodeException error = assertThrows(DecodeException.class, () -> budget.enter(5));
        assertEquals(List.of(Reason.TOO_DEEP, 5), List.of(error.getReason(), error.getOffset()));
    }

    @Test
    void leavingFreesADepthLevel() {
        DecodeBudget budget = new DecodeBudget(new DecodeLimits(10, 100, 1));
        budget.enter(0);
        budget.leave();
        assertDoesNotThrow(() -> budget.enter(0));
    }

    @Test
    void depthIsCappedAt128() {
        assertEquals(128, new DecodeLimits(10, 100, 1000).maxDepth());
    }
}
