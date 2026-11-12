package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import dev.endstone.protocol.DecodeException.Reason;
import dev.endstone.protocol.DynamicValue.ArrayValue;
import dev.endstone.protocol.DynamicValue.BoolValue;
import dev.endstone.protocol.DynamicValue.IntegerValue;
import dev.endstone.protocol.DynamicValue.NullValue;
import dev.endstone.protocol.DynamicValue.NumberValue;
import dev.endstone.protocol.DynamicValue.ObjectValue;
import dev.endstone.protocol.DynamicValue.StringValue;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

class DynamicValueTest {
    static Stream<Arguments> values() {
        return Stream.of(
                argumentSet("null", new NullValue(), "00000000"),
                argumentSet("bool", new BoolValue(true), "0100000001"),
                argumentSet("integer", new IntegerValue(-2L), "02000000feffffffffffffff"),
                argumentSet("number", new NumberValue(1.0), "03000000000000000000f03f"),
                argumentSet("string", new StringValue("hi"), "04000000026869"),
                argumentSet(
                        "array", new ArrayValue(List.of(new NullValue())), "050000000100000000"),
                argumentSet(
                        "array two groups",
                        new ArrayValue(Collections.nCopies(128, new NullValue())),
                        "05000000" + "8001" + "00000000".repeat(128)),
                argumentSet(
                        "object",
                        new ObjectValue(Map.of("b", new NullValue(), "a", new BoolValue(true))),
                        "0600000002" + "0161" + "0100000001" + "0162" + "00000000"));
    }

    private static ByteBuf hex(String hex) {
        return Unpooled.wrappedBuffer(ByteBufUtil.decodeHexDump(hex));
    }

    private static DynamicValue decode(String hex) {
        return Wire.decode(hex(hex), DecodeLimits.DEFAULT, "DynamicValue", DynamicValue::read);
    }

    private static DecodeException fail(String hex) {
        return assertThrows(DecodeException.class, () -> decode(hex));
    }

    @ParameterizedTest
    @MethodSource("values")
    void encodeWritesTheTagThenThePayload(DynamicValue value, String hex) {
        ByteBuf buf = Unpooled.buffer();
        value.encode(buf);
        assertEquals(hex, ByteBufUtil.hexDump(buf));
    }

    @ParameterizedTest
    @MethodSource("values")
    void readReadsTheTagThenThePayload(DynamicValue value, String hex) {
        assertEquals(value, decode(hex));
    }

    @Test
    void objectKeysAreWrittenInUnsignedByteOrder() {
        ByteBuf buf = Unpooled.buffer();
        new ObjectValue(Map.of("𐀀", new NullValue(), "￿", new NullValue())).encode(buf);
        assertEquals(
                "0600000002" + "03efbfbf00000000" + "04f090808000000000", ByteBufUtil.hexDump(buf));
    }

    @Test
    void aDuplicateKeyKeepsTheFirstValue() {
        assertEquals(
                new ObjectValue(Map.of("a", new NullValue())),
                decode("0600000002" + "016100000000" + "01610100000001"));
    }

    @Test
    void anUnknownTagIsAnUnknownValue() {
        assertEquals("DynamicValue: unknown value at byte 4 of 4", fail("07000000").getMessage());
        assertEquals(Reason.UNKNOWN_VALUE, fail("ffffffff").getReason());
    }

    @Test
    void aMissingPayloadIsTruncated() {
        assertEquals("DynamicValue: truncated at byte 4 of 4", fail("01000000").getMessage());
    }

    @Test
    void bytesAfterTheValueAreTrailing() {
        assertEquals(
                "DynamicValue: trailing bytes at byte 4 of 5", fail("0000000000").getMessage());
    }

    @Test
    void aValueNested129DeepIsTooDeep() {
        DecodeException error = fail("0500000001".repeat(128) + "00000000");
        assertEquals("DynamicValue: too deep at byte 640 of 644", error.getMessage());
    }

    @Test
    void aValueNested128DeepIsAccepted() {
        assertDoesNotThrow(() -> decode("0500000001".repeat(127) + "00000000"));
    }

    @Test
    void anArrayPastTheElementLimitIsTooLarge() {
        DecodeException error =
                assertThrows(
                        DecodeException.class,
                        () ->
                                Wire.decode(
                                        hex("0500000002"),
                                        new DecodeLimits(1, 1_000L, 128),
                                        "DynamicValue",
                                        DynamicValue::read));
        assertEquals("DynamicValue: too large at byte 5 of 5", error.getMessage());
    }

    @Test
    void aStringValueRejectsNull() {
        assertEquals(
                "StringValue.value",
                assertThrows(NullPointerException.class, () -> new StringValue(null)).getMessage());
    }
}
