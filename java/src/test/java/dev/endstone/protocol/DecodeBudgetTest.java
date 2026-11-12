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
        assertThrows(
                IllegalArgumentException.class, () -> new DecodeLimits(elements, bytes, depth));
    }

    @Test
    void elementLimitIsAllowedAndOneMoreIsTooLarge() {
        DecodeBudget budget = new DecodeBudget(new DecodeLimits(10, 100, 4));
        assertDoesNotThrow(() -> budget.chargeElements(10, 0));
        DecodeException error =
                assertThrows(DecodeException.class, () -> budget.chargeElements(1, 3));
        assertEquals(List.of(Reason.TOO_LARGE, 3), List.of(error.getReason(), error.getOffset()));
    }

    @Test
    void elementChargesAccumulate() {
        DecodeBudget budget = new DecodeBudget(new DecodeLimits(10, 100, 4));
        budget.chargeElements(6, 0);
        assertThrows(DecodeException.class, () -> budget.chargeElements(5, 0));
    }

    @Test
    void byteLimitIsAllowedAndOneMoreIsTooLarge() {
        DecodeBudget budget = new DecodeBudget(new DecodeLimits(10, 100, 4));
        assertDoesNotThrow(() -> budget.chargeBytes(100, 0));
        DecodeException error = assertThrows(DecodeException.class, () -> budget.chargeBytes(1, 9));
        assertEquals(List.of(Reason.TOO_LARGE, 9), List.of(error.getReason(), error.getOffset()));
    }

    @Test
    void hugeChargeDoesNotOverflow() {
        DecodeBudget budget = new DecodeBudget(new DecodeLimits(10, 100, 4));
        budget.chargeBytes(1, 0);
        assertThrows(DecodeException.class, () -> budget.chargeBytes(Long.MAX_VALUE, 0));
    }

    @Test
    void depthLimitIsAllowedAndOneMoreIsTooDeep() {
        DecodeBudget budget = new DecodeBudget();
        for (int level = 0; level < 128; level++) {
            budget.enter(0);
        }
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
        assertEquals(128, new DecodeBudget(new DecodeLimits(10, 100, 1000)).maxDepth());
    }
}
