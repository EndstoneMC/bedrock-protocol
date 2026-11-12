package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import dev.endstone.protocol.DecodeException.Reason;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import java.util.BitSet;
import java.util.List;
import java.util.UUID;
import java.util.function.Consumer;
import java.util.function.ObjIntConsumer;
import java.util.function.ObjLongConsumer;
import java.util.function.ToIntFunction;
import java.util.function.ToLongFunction;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

class WireTest {
    private static ByteBuf hex(String hex) {
        return Unpooled.wrappedBuffer(ByteBufUtil.decodeHexDump(hex));
    }

    private static String written(ByteBuf buf) {
        return ByteBufUtil.hexDump(buf);
    }

    private static DecodeBudget budget() {
        return new DecodeBudget(DecodeLimits.DEFAULT);
    }

    private static DecodeException failure(Runnable read) {
        return assertThrows(DecodeException.class, read::run);
    }

    private static List<Object> reasonAndOffset(DecodeException error) {
        return List.of(error.getReason(), error.getOffset());
    }

    static Stream<Arguments> varint32() {
        ToIntFunction<ByteBuf> unsignedRead = Wire::readUvarint32;
        ToIntFunction<ByteBuf> zigzagRead = Wire::readVarint32;
        ObjIntConsumer<ByteBuf> unsignedWrite = Wire::writeUvarint32;
        ObjIntConsumer<ByteBuf> zigzagWrite = Wire::writeVarint32;
        return Stream.of(
                argumentSet("unsigned zero", "00", 0, unsignedRead, unsignedWrite),
                argumentSet("unsigned 300", "ac02", 300, unsignedRead, unsignedWrite),
                argumentSet("unsigned all bits", "ffffffff0f", -1, unsignedRead, unsignedWrite),
                argumentSet("zigzag zero", "00", 0, zigzagRead, zigzagWrite),
                argumentSet("zigzag minus one", "01", -1, zigzagRead, zigzagWrite),
                argumentSet("zigzag one", "02", 1, zigzagRead, zigzagWrite),
                argumentSet(
                        "zigzag minimum", "ffffffff0f", Integer.MIN_VALUE, zigzagRead, zigzagWrite),
                argumentSet(
                        "zigzag maximum",
                        "feffffff0f",
                        Integer.MAX_VALUE,
                        zigzagRead,
                        zigzagWrite));
    }

    static Stream<Arguments> varint64() {
        ToLongFunction<ByteBuf> unsignedRead = Wire::readUvarint64;
        ToLongFunction<ByteBuf> zigzagRead = Wire::readVarint64;
        ObjLongConsumer<ByteBuf> unsignedWrite = Wire::writeUvarint64;
        ObjLongConsumer<ByteBuf> zigzagWrite = Wire::writeVarint64;
        return Stream.of(
                argumentSet("unsigned 300", "ac02", 300L, unsignedRead, unsignedWrite),
                argumentSet(
                        "unsigned all bits",
                        "ffffffffffffffffff01",
                        -1L,
                        unsignedRead,
                        unsignedWrite),
                argumentSet("zigzag minus one", "01", -1L, zigzagRead, zigzagWrite),
                argumentSet(
                        "zigzag minimum",
                        "ffffffffffffffffff01",
                        Long.MIN_VALUE,
                        zigzagRead,
                        zigzagWrite),
                argumentSet(
                        "zigzag maximum",
                        "feffffffffffffffff01",
                        Long.MAX_VALUE,
                        zigzagRead,
                        zigzagWrite));
    }

    static Stream<Arguments> fixedReads() {
        return Stream.of(
                argumentSet("bool", (Consumer<ByteBuf>) Wire::readBool, 1),
                argumentSet("int8", (Consumer<ByteBuf>) Wire::readInt8, 1),
                argumentSet("uint8", (Consumer<ByteBuf>) Wire::readUint8, 1),
                argumentSet("int16", (Consumer<ByteBuf>) Wire::readInt16, 2),
                argumentSet("uint16", (Consumer<ByteBuf>) Wire::readUint16, 2),
                argumentSet("int32", (Consumer<ByteBuf>) Wire::readInt32, 4),
                argumentSet("int64", (Consumer<ByteBuf>) Wire::readInt64, 8),
                argumentSet("float", (Consumer<ByteBuf>) Wire::readFloat, 4),
                argumentSet("double", (Consumer<ByteBuf>) Wire::readDouble, 8),
                argumentSet("int32 big endian", (Consumer<ByteBuf>) Wire::readInt32Be, 4));
    }

    static Stream<Arguments> strings() {
        return Stream.of(
                argumentSet("ascii", "0161", "a"),
                argumentSet("two-byte", "02c3a9", "é"),
                argumentSet("supplementary", "04f0908080", "𐀀"),
                argumentSet("lone escape", "01ff", "\udcff"),
                argumentSet("encoded surrogate", "03eda080", "\udced\udca0\udc80"),
                argumentSet("overlong", "02c080", "\udcc0\udc80"),
                argumentSet("past the last code point", "04f4908080", "\udcf4\udc90\udc80\udc80"),
                argumentSet("cut-off sequence", "02e182", "\udce1\udc82"),
                argumentSet("empty", "00", ""));
    }

    @ParameterizedTest
    @MethodSource("varint32")
    void varint32Reads(
            String hex, int expected, ToIntFunction<ByteBuf> read, ObjIntConsumer<ByteBuf> write) {
        assertEquals(expected, read.applyAsInt(hex(hex)));
    }

    @ParameterizedTest
    @MethodSource("varint32")
    void varint32Writes(
            String hex, int value, ToIntFunction<ByteBuf> read, ObjIntConsumer<ByteBuf> write) {
        ByteBuf buf = Unpooled.buffer();
        write.accept(buf, value);
        assertEquals(hex, written(buf));
    }

    @ParameterizedTest
    @MethodSource("varint64")
    void varint64Reads(
            String hex,
            long expected,
            ToLongFunction<ByteBuf> read,
            ObjLongConsumer<ByteBuf> write) {
        assertEquals(expected, read.applyAsLong(hex(hex)));
    }

    @ParameterizedTest
    @MethodSource("varint64")
    void varint64Writes(
            String hex, long value, ToLongFunction<ByteBuf> read, ObjLongConsumer<ByteBuf> write) {
        ByteBuf buf = Unpooled.buffer();
        write.accept(buf, value);
        assertEquals(hex, written(buf));
    }

    @Test
    void uvarint32PastItsTypeIsOutOfRangeAfterTheFifthByte() {
        DecodeException error = failure(() -> Wire.readUvarint32(hex("ffffffff10")));
        assertEquals(List.of(Reason.OUT_OF_RANGE, 5), reasonAndOffset(error));
    }

    @Test
    void uvarint32WithAContinuationAfterTheFifthByteIsOutOfRange() {
        DecodeException error = failure(() -> Wire.readUvarint32(hex("ffffffff8f00")));
        assertEquals(List.of(Reason.OUT_OF_RANGE, 5), reasonAndOffset(error));
    }

    @Test
    void uvarint64PastItsTypeIsOutOfRangeAfterTheTenthByte() {
        DecodeException error = failure(() -> Wire.readUvarint64(hex("ffffffffffffffffff02")));
        assertEquals(List.of(Reason.OUT_OF_RANGE, 10), reasonAndOffset(error));
    }

    @Test
    void varintThatRunsOutIsTruncatedAtTheEndOfTheInput() {
        DecodeException error = failure(() -> Wire.readUvarint32(hex("8080")));
        assertEquals(List.of(Reason.TRUNCATED, 2), reasonAndOffset(error));
    }

    @Test
    void fixedWidthTruncationReportsTheFieldStart() {
        ByteBuf buf = hex("aabb01020304");
        buf.readerIndex(2);
        DecodeException error = failure(() -> Wire.readInt64(buf));
        assertEquals(List.of(Reason.TRUNCATED, 2), reasonAndOffset(error));
    }

    @ParameterizedTest
    @MethodSource("fixedReads")
    void everyFixedReadOneByteShortIsTruncatedAtTheFieldStart(Consumer<ByteBuf> read, int width) {
        ByteBuf buf = Unpooled.wrappedBuffer(new byte[width - 1]);
        DecodeException error = failure(() -> read.accept(buf));
        assertEquals(List.of(Reason.TRUNCATED, 0), reasonAndOffset(error));
    }

    @ParameterizedTest
    @MethodSource("fixedReads")
    void everyFixedReadConsumesExactlyItsWidth(Consumer<ByteBuf> read, int width) {
        ByteBuf buf = Unpooled.wrappedBuffer(new byte[width + 1]);
        read.accept(buf);
        assertEquals(1, buf.readableBytes());
    }

    @Test
    void littleEndianAndBigEndianReadsDisagreeOnTheSameBytes() {
        assertEquals(0x04030201, Wire.readInt32(hex("01020304")));
        assertEquals(0x01020304, Wire.readInt32Be(hex("01020304")));
    }

    @Test
    void uint8DoesNotSignExtend() {
        assertEquals(255, Wire.readUint8(hex("ff")));
    }

    @Test
    void uint16DoesNotSignExtend() {
        assertEquals(65535, Wire.readUint16(hex("ffff")));
    }

    @Test
    void floatReadsLittleEndian() {
        assertEquals(1.0f, Wire.readFloat(hex("0000803f")));
    }

    @Test
    void doubleReadsLittleEndian() {
        assertEquals(1.0, Wire.readDouble(hex("000000000000f03f")));
    }

    @Test
    void boolReadsAnyNonZeroByteAsTrue() {
        assertTrue(Wire.readBool(hex("02")));
    }

    @ParameterizedTest
    @MethodSource("strings")
    void strReads(String hex, String expected) {
        assertEquals(expected, Wire.readStr(hex(hex), budget()));
    }

    @ParameterizedTest
    @MethodSource("strings")
    void strWritesWhatItRead(String hex, String value) {
        ByteBuf buf = Unpooled.buffer();
        Wire.writeStr(buf, value);
        assertEquals(hex, written(buf));
    }

    @Test
    void strLengthPastTheBodyIsTruncatedBeforeAnyAllocation() {
        ByteBuf buf = hex("ffffffff0f");
        DecodeException error = failure(() -> Wire.readStr(buf, budget()));
        assertEquals(List.of(Reason.TRUNCATED, 5), reasonAndOffset(error));
    }

    @Test
    void strChargesItsBytesToTheBudget() {
        DecodeBudget small = new DecodeBudget(new DecodeLimits(10, 1, 4));
        DecodeException error = failure(() -> Wire.readStr(hex("026162"), small));
        assertEquals(List.of(Reason.TOO_LARGE, 1), reasonAndOffset(error));
    }

    @Test
    void writingAnUnpairedHighSurrogateIsRejected() {
        ByteBuf buf = Unpooled.buffer();
        IllegalArgumentException error =
                assertThrows(IllegalArgumentException.class, () -> Wire.writeStr(buf, "\ud800"));
        assertEquals("string has an unpaired surrogate at index 0", error.getMessage());
    }

    @Test
    void rejectedStringLeavesTheBufferEmpty() {
        ByteBuf buf = Unpooled.buffer();
        assertThrows(IllegalArgumentException.class, () -> Wire.writeStr(buf, "a\udbff"));
        assertEquals(0, buf.readableBytes());
    }

    @Test
    void bytesWriteTheirLengthPrefix() {
        ByteBuf buf = Unpooled.buffer();
        Wire.writeBytes(buf, new byte[] {1, 2, 3});
        assertEquals("03010203", written(buf));
    }

    @Test
    void bytesReadTheirLengthPrefix() {
        assertArrayEquals(new byte[] {1, 2, 3}, Wire.readBytes(hex("03010203"), budget()));
    }

    @Test
    void uuidIsTwoLittleEndianLongsMostSignificantFirst() {
        UUID uuid = Wire.readUuid(hex("0807060504030201100f0e0d0c0b0a09"));
        assertEquals(new UUID(0x0102030405060708L, 0x090a0b0c0d0e0f10L), uuid);
    }

    @Test
    void uuidWithOnlyTheFirstLongAndAPartIsTruncatedAtTheSecondLong() {
        DecodeException error = failure(() -> Wire.readUuid(Unpooled.wrappedBuffer(new byte[12])));
        assertEquals(List.of(Reason.TRUNCATED, 8), reasonAndOffset(error));
    }

    @Test
    void uuidWritesMostSignificantLongFirst() {
        ByteBuf buf = Unpooled.buffer();
        Wire.writeUuid(buf, new UUID(0x0102030405060708L, 0x090a0b0c0d0e0f10L));
        assertEquals("0807060504030201100f0e0d0c0b0a09", written(buf));
    }

    static Stream<Arguments> bitsets() {
        return Stream.of(
                argumentSet("empty", "00", 30, new BitSet()),
                argumentSet("bit zero", "01", 30, BitSet.valueOf(new long[] {0x01})),
                argumentSet("bit seven", "8001", 30, BitSet.valueOf(new long[] {0x80})),
                argumentSet("bits in two groups", "8101", 30, BitSet.valueOf(new long[] {0x81})),
                argumentSet(
                        "last bit of the width",
                        "808080808001",
                        36,
                        BitSet.valueOf(new long[] {1L << 35})));
    }

    @ParameterizedTest
    @MethodSource("bitsets")
    void bitsetReads(String hex, int width, BitSet expected) {
        assertEquals(expected, Wire.readBitset(hex(hex), width));
    }

    @Test
    void bitsetWritesGroupsUpToTheHighestBit() {
        BitSet bits = new BitSet();
        bits.set(0);
        bits.set(7);
        ByteBuf buf = Unpooled.buffer();
        Wire.writeBitset(buf, bits, 30, "flags");
        assertEquals("8101", written(buf));
    }

    @Test
    void emptyBitsetWritesOneGroup() {
        ByteBuf buf = Unpooled.buffer();
        Wire.writeBitset(buf, new BitSet(), 30, "flags");
        assertEquals("00", written(buf));
    }

    @Test
    void bitsetBitAtTheWidthIsOutOfRange() {
        DecodeException error = failure(() -> Wire.readBitset(hex("08"), 3));
        assertEquals(List.of(Reason.OUT_OF_RANGE, 1), reasonAndOffset(error));
    }

    @Test
    void bitsetContinuationIntoAGroupAtTheWidthIsOutOfRange() {
        DecodeException error = failure(() -> Wire.readBitset(hex("8000"), 7));
        assertEquals(List.of(Reason.OUT_OF_RANGE, 1), reasonAndOffset(error));
    }

    @Test
    void bitsetThatRunsOutIsTruncated() {
        DecodeException error = failure(() -> Wire.readBitset(hex("80"), 30));
        assertEquals(List.of(Reason.TRUNCATED, 1), reasonAndOffset(error));
    }

    @Test
    void bitsetPastItsWidthIsRejectedOnEncode() {
        BitSet bits = new BitSet();
        bits.set(5);
        IllegalStateException error =
                assertThrows(
                        IllegalStateException.class,
                        () -> Wire.writeBitset(Unpooled.buffer(), bits, 5, "Pack.flags"));
        assertEquals("Pack.flags: bit 5 is past the width 5", error.getMessage());
    }

    @Test
    void strOrderPutsASupplementaryCharacterAfterAHighBmpOne() {
        assertTrue(Wire.STR_ORDER.compare("\uffff", "\ud800\udc00") < 0);
        assertTrue("\uffff".compareTo("\ud800\udc00") > 0);
    }

    @Test
    void strOrderPutsAnEscapedByteBeforeALetterWithAccent() {
        assertTrue(Wire.STR_ORDER.compare("\udc80", "é") < 0);
        assertTrue("\udc80".compareTo("é") > 0);
    }

    @Test
    void strOrderTreatsAPrefixAsSmaller() {
        assertTrue(Wire.STR_ORDER.compare("ab", "abc") < 0);
    }

    @Test
    void foldAsciiLowersLettersOnly() {
        assertEquals("abc_1", Wire.foldAscii("AbC_1"));
    }

    @Test
    void foldAsciiLeavesTheKelvinSignAlone() {
        assertEquals("\u212a", Wire.foldAscii("\u212a"));
    }

    @Test
    void decodeReturnsTheValue() {
        int value =
                Wire.decode(hex("2a"), DecodeLimits.DEFAULT, "T", (b, budget) -> Wire.readUint8(b));
        assertEquals(42, value);
    }

    @Test
    void decodeConsumesTheInput() {
        ByteBuf buf = hex("2a");
        Wire.decode(buf, DecodeLimits.DEFAULT, "T", (b, budget) -> Wire.readUint8(b));
        assertEquals(0, buf.readableBytes());
    }

    @Test
    void decodeReportsTrailingBytesAtTheEndOfTheValue() {
        ByteBuf buf = hex("2a0000");
        DecodeException error =
                assertThrows(
                        DecodeException.class,
                        () ->
                                Wire.decode(
                                        buf,
                                        DecodeLimits.DEFAULT,
                                        "PlayStatusPacket",
                                        (b, budget) -> Wire.readUint8(b)));
        assertEquals("PlayStatusPacket: trailing bytes at byte 1 of 3", error.getMessage());
    }

    @Test
    void decodeRestoresTheReaderIndexOnFailure() {
        ByteBuf buf = hex("ff2a0000");
        buf.readerIndex(1);
        assertThrows(
                DecodeException.class,
                () ->
                        Wire.decode(
                                buf, DecodeLimits.DEFAULT, "T", (b, budget) -> Wire.readInt64(b)));
        assertEquals(1, buf.readerIndex());
    }

    @Test
    void decodeStampsTheTypeAndCountsFromTheFirstByteHandedIn() {
        ByteBuf buf = hex("ff0102");
        buf.readerIndex(1);
        DecodeException error =
                assertThrows(
                        DecodeException.class,
                        () ->
                                Wire.decode(
                                        buf,
                                        DecodeLimits.DEFAULT,
                                        "PlayStatusPacket",
                                        (b, budget) -> Wire.readInt32(b)));
        assertEquals("PlayStatusPacket: truncated at byte 0 of 2", error.getMessage());
    }

    @Test
    void decodeGivesEachCallItsOwnBudget() {
        DecodeLimits limits = new DecodeLimits(10, 1, 4);
        Decoder<String> reader = (b, budget) -> Wire.readStr(b, budget);
        assertEquals("a", Wire.decode(hex("0161"), limits, "T", reader));
        assertEquals("b", Wire.decode(hex("0162"), limits, "T", reader));
    }

    static Stream<Arguments> countReads() {
        ToLongFunction<ByteBuf> uvarint32 = Wire::readUvarint32Count;
        ToLongFunction<ByteBuf> uint32 = Wire::readUint32Count;
        ToLongFunction<ByteBuf> uint16 = Wire::readUint16Count;
        ToLongFunction<ByteBuf> varint32 = Wire::readVarint32Count;
        return Stream.of(
                argumentSet("uvarint32", "ffffffff0f", uvarint32, 4_294_967_295L),
                argumentSet("uint32", "ffffffff", uint32, 4_294_967_295L),
                argumentSet("uint16", "ffff", uint16, 65_535L),
                argumentSet("varint32", "01", varint32, -1L));
    }

    @ParameterizedTest
    @MethodSource("countReads")
    void countPrefixesReadAsTheirDeclaredSign(
            String hex, ToLongFunction<ByteBuf> read, long expected) {
        assertEquals(expected, read.applyAsLong(hex(hex)));
    }

    @Test
    void negativeCountIsOutOfRangeWhenCharged() {
        ByteBuf buf = hex("01");
        long count = Wire.readVarint32Count(buf);
        DecodeException error = failure(() -> Wire.charge(buf, budget(), count, 4));
        assertEquals(List.of(Reason.OUT_OF_RANGE, 1), reasonAndOffset(error));
    }

    @Test
    void countPastTheElementLimitIsTooLarge() {
        DecodeBudget small = new DecodeBudget(new DecodeLimits(2, 100, 4));
        DecodeException error = failure(() -> Wire.charge(hex("00"), small, 3, 0));
        assertEquals(List.of(Reason.TOO_LARGE, 0), reasonAndOffset(error));
    }

    @Test
    void countTimesWidthPastTheByteLimitIsTooLarge() {
        DecodeBudget small = new DecodeBudget(new DecodeLimits(10, 8, 4));
        DecodeException error = failure(() -> Wire.charge(hex("00"), small, 3, 4));
        assertEquals(List.of(Reason.TOO_LARGE, 0), reasonAndOffset(error));
    }

    @Test
    void chargeReturnsTheCount() {
        assertEquals(3, Wire.charge(hex("00"), budget(), 3, 4));
    }

    @Test
    void negativeCountFactorIsOutOfRange() {
        DecodeException error = failure(() -> Wire.countValue(hex("00"), -1));
        assertEquals(List.of(Reason.OUT_OF_RANGE, 0), reasonAndOffset(error));
    }

    @Test
    void negativeFactorInAProductIsOutOfRange() {
        DecodeException error = failure(() -> Wire.countProduct(hex("00"), 4, -1));
        assertEquals(List.of(Reason.OUT_OF_RANGE, 0), reasonAndOffset(error));
    }

    @Test
    void productPastSixtyFourBitsIsOutOfRange() {
        DecodeException error = failure(() -> Wire.countProduct(hex("00"), 1L << 32, 1L << 32));
        assertEquals(List.of(Reason.OUT_OF_RANGE, 0), reasonAndOffset(error));
    }

    @Test
    void productIsChargedAsALong() {
        ByteBuf buf = hex("00");
        long count = Wire.countProduct(buf, 65_536, 65_536);
        DecodeException error = failure(() -> Wire.charge(buf, budget(), count, 0));
        assertEquals(List.of(Reason.TOO_LARGE, 0), reasonAndOffset(error));
    }

    @Test
    void primitiveArrayThatRunsShortIsTruncatedAtTheFirstElementThatDoesNotFit() {
        ByteBuf buf = Unpooled.wrappedBuffer(new byte[10]);
        DecodeException error = failure(() -> Wire.needElements(buf, 3, 4));
        assertEquals(List.of(Reason.TRUNCATED, 8), reasonAndOffset(error));
    }

    @Test
    void primitiveArrayThatRunsShortNamesTheElementIndex() {
        ByteBuf buf = Unpooled.wrappedBuffer(new byte[10]);
        DecodeException error = failure(() -> Wire.needElements(buf, 3, 4));
        assertEquals(List.of(2), error.getPath());
    }

    @Test
    void primitiveArrayThatFitsIsAccepted() {
        ByteBuf buf = Unpooled.wrappedBuffer(new byte[12]);
        assertDoesNotThrow(() -> Wire.needElements(buf, 3, 4));
    }

    @Test
    void initialCapacityOfAnAdmittedHostileCountIsCapped() {
        ByteBuf buf = hex("c0843d");
        int count = Wire.charge(buf, budget(), Wire.readUvarint32Count(buf), 0);
        assertEquals(65_536, Wire.initialCapacity(count));
    }

    @Test
    void initialCapacityKeepsASmallCount() {
        assertEquals(3, Wire.initialCapacity(3));
    }
}
