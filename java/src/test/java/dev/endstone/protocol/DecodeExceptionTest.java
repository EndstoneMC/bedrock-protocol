package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import dev.endstone.protocol.DecodeException.Reason;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

class DecodeExceptionTest {
    static Stream<Arguments> reasonTexts() {
        return Stream.of(
                argumentSet("truncated", Reason.TRUNCATED, "truncated"),
                argumentSet("out of range", Reason.OUT_OF_RANGE, "out of range"),
                argumentSet("unknown value", Reason.UNKNOWN_VALUE, "unknown value"),
                argumentSet("too large", Reason.TOO_LARGE, "too large"),
                argumentSet("too deep", Reason.TOO_DEEP, "too deep"),
                argumentSet("trailing bytes", Reason.TRAILING_BYTES, "trailing bytes"));
    }

    @Test
    void isUnchecked() {
        assertInstanceOf(RuntimeException.class, new DecodeException(Reason.TRUNCATED, 0));
    }

    @Test
    void reasonsFollowTheCppOrder() {
        assertEquals(
                List.of(
                        Reason.TRUNCATED,
                        Reason.OUT_OF_RANGE,
                        Reason.UNKNOWN_VALUE,
                        Reason.TOO_LARGE,
                        Reason.TOO_DEEP,
                        Reason.TRAILING_BYTES),
                List.of(Reason.values()));
    }

    @ParameterizedTest
    @MethodSource("reasonTexts")
    void messageSpellsTheReason(Reason reason, String text) {
        DecodeException error = new DecodeException(reason, 2);
        error.stamp("T", 2, 5);
        assertEquals("T: " + text + " at byte 2 of 5", error.getMessage());
    }

    @Test
    void messageNamesTheTypeFieldAndOffset() {
        DecodeException error = new DecodeException(Reason.TRUNCATED, 0).prepend("status");
        error.stamp("PlayStatusPacket", 0, 3);
        assertEquals("PlayStatusPacket.status: truncated at byte 0 of 3", error.getMessage());
    }

    @Test
    void prependsLeaveThePathOuterFirst() {
        DecodeException error =
                new DecodeException(Reason.OUT_OF_RANGE, 7).prepend("b").prepend(3).prepend("a");
        error.stamp("Type", 7, 9);
        assertEquals(List.of("a", 3, "b"), error.getPath());
        assertEquals("Type.a[3].b: out of range at byte 7 of 9", error.getMessage());
    }

    @Test
    void prependReturnsTheSameInstance() {
        DecodeException error = new DecodeException(Reason.TRUNCATED, 0);
        assertSame(error, error.prepend("x"));
        assertSame(error, error.prepend(1));
    }

    @Test
    void stampReplacesTheOffsetAndRecordsTheLength() {
        DecodeException error = new DecodeException(Reason.TRUNCATED, 10);
        error.stamp("Type", 4, 12);
        assertEquals(
                List.of("Type", 4, 12),
                List.of(error.getType(), error.getOffset(), error.getLength()));
    }

    @Test
    void serialisationKeepsEveryField() throws IOException, ClassNotFoundException {
        DecodeException error =
                new DecodeException(Reason.UNKNOWN_VALUE, 6).prepend(2).prepend("list");
        error.stamp("Type", 6, 8);
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (ObjectOutputStream out = new ObjectOutputStream(bytes)) {
            out.writeObject(error);
        }
        try (ObjectInputStream in =
                new ObjectInputStream(new ByteArrayInputStream(bytes.toByteArray()))) {
            DecodeException copy = assertInstanceOf(DecodeException.class, in.readObject());
            assertEquals(
                    List.of(Reason.UNKNOWN_VALUE, "Type", List.of("list", 2), 6, 8),
                    List.of(
                            copy.getReason(),
                            copy.getType(),
                            copy.getPath(),
                            copy.getOffset(),
                            copy.getLength()));
        }
    }
}
