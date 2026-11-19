package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.util.List;
import java.util.function.IntFunction;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

final class DecodeExceptionTest {
    static Stream<Arguments> factories() {
        return Stream.of(
                argumentSet(
                        "truncated",
                        (IntFunction<DecodeException>) DecodeException::truncated,
                        "truncated"),
                argumentSet(
                        "out of range",
                        (IntFunction<DecodeException>) DecodeException::outOfRange,
                        "out of range"),
                argumentSet(
                        "unknown value",
                        (IntFunction<DecodeException>) DecodeException::unknownValue,
                        "unknown value"),
                argumentSet(
                        "trailing bytes",
                        (IntFunction<DecodeException>) DecodeException::trailingBytes,
                        "trailing bytes"));
    }

    @Test
    void isUnchecked() {
        assertInstanceOf(RuntimeException.class, DecodeException.truncated(0));
    }

    @ParameterizedTest
    @MethodSource("factories")
    void eachFactorySpellsItsReasonInTheMessage(IntFunction<DecodeException> factory, String text) {
        DecodeException error = factory.apply(2);
        error.stamp("T", 2, 5);
        assertEquals("T: " + text + " at byte 2 of 5", error.getMessage());
    }

    @Test
    void messageNamesTheTypeFieldAndOffset() {
        DecodeException error = DecodeException.truncated(0).prepend("status");
        error.stamp("PlayStatusPacket", 0, 3);
        assertEquals("PlayStatusPacket.status: truncated at byte 0 of 3", error.getMessage());
    }

    @Test
    void prependsLeaveThePathOuterFirst() {
        DecodeException error = DecodeException.outOfRange(7).prepend("b").prepend(3).prepend("a");
        error.stamp("Type", 7, 9);
        assertEquals(List.of("a", 3, "b"), error.getPath());
    }

    @Test
    void messageRendersThePathWithBracketedIndexes() {
        DecodeException error = DecodeException.outOfRange(7).prepend("b").prepend(3).prepend("a");
        error.stamp("Type", 7, 9);
        assertEquals("Type.a[3].b: out of range at byte 7 of 9", error.getMessage());
    }

    @Test
    void prependReturnsTheSameInstance() {
        DecodeException error = DecodeException.truncated(0);
        assertSame(error, error.prepend("x"));
        assertSame(error, error.prepend(1));
    }

    @Test
    void stampRecordsTheType() {
        DecodeException error = DecodeException.truncated(10);
        error.stamp("Type", 4, 12);
        assertEquals("Type", error.getType());
    }

    @Test
    void stampReplacesTheOffset() {
        DecodeException error = DecodeException.truncated(10);
        error.stamp("Type", 4, 12);
        assertEquals(4, error.getOffset());
    }

    @Test
    void stampRecordsTheLength() {
        DecodeException error = DecodeException.truncated(10);
        error.stamp("Type", 4, 12);
        assertEquals(12, error.getLength());
    }

    private static DecodeException roundTrip(DecodeException error)
            throws IOException, ClassNotFoundException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        ObjectOutputStream out = new ObjectOutputStream(bytes);
        out.writeObject(error);
        out.flush();
        return assertInstanceOf(
                DecodeException.class,
                new ObjectInputStream(new ByteArrayInputStream(bytes.toByteArray())).readObject());
    }

    @Test
    void serialisationKeepsEveryField() throws IOException, ClassNotFoundException {
        DecodeException error = DecodeException.unknownValue(6).prepend(2).prepend("list");
        error.stamp("Type", 6, 8);
        assertEquals("Type.list[2]: unknown value at byte 6 of 8", roundTrip(error).getMessage());
    }

    @Test
    void aFreshExceptionHasNoUnfinishedMessage() {
        assertNull(DecodeException.truncated(0).getUnfinishedMessage());
    }

    @Test
    void serialisationDropsTheUnfinishedMessage() throws IOException, ClassNotFoundException {
        DecodeException error =
                DecodeException.truncated(0)
                        .setUnfinishedMessage(ToastRequestPacket.getDefaultInstance());
        assertNull(roundTrip(error).getUnfinishedMessage());
    }
}
