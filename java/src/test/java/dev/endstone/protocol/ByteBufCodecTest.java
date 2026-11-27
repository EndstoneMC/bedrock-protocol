package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import java.nio.charset.StandardCharsets;
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

final class ByteBufCodecTest {
  private static ByteBuf hex(String hex) {
    return Unpooled.wrappedBuffer(ByteBufUtil.decodeHexDump(hex));
  }

  private static String written(ByteBuf buf) {
    return ByteBufUtil.hexDump(buf);
  }

  private static DecodeException failure(Runnable read) {
    return assertThrows(DecodeException.class, read::run);
  }

  static Stream<Arguments> varint32() {
    ToIntFunction<ByteBuf> unsignedRead = ByteBufCodec::readUnsignedVarInt;
    ToIntFunction<ByteBuf> zigzagRead = ByteBufCodec::readVarInt;
    ObjIntConsumer<ByteBuf> unsignedWrite = ByteBufCodec::writeUnsignedVarInt;
    ObjIntConsumer<ByteBuf> zigzagWrite = ByteBufCodec::writeVarInt;
    return Stream.of(
        argumentSet("unsigned zero", "00", 0, unsignedRead, unsignedWrite),
        argumentSet("unsigned 300", "ac02", 300, unsignedRead, unsignedWrite),
        argumentSet("unsigned all bits", "ffffffff0f", -1, unsignedRead, unsignedWrite),
        argumentSet("zigzag zero", "00", 0, zigzagRead, zigzagWrite),
        argumentSet("zigzag minus one", "01", -1, zigzagRead, zigzagWrite),
        argumentSet("zigzag one", "02", 1, zigzagRead, zigzagWrite),
        argumentSet("zigzag minimum", "ffffffff0f", Integer.MIN_VALUE, zigzagRead, zigzagWrite),
        argumentSet("zigzag maximum", "feffffff0f", Integer.MAX_VALUE, zigzagRead, zigzagWrite));
  }

  static Stream<Arguments> varint64() {
    ToLongFunction<ByteBuf> unsignedRead = ByteBufCodec::readUnsignedVarLong;
    ToLongFunction<ByteBuf> zigzagRead = ByteBufCodec::readVarLong;
    ObjLongConsumer<ByteBuf> unsignedWrite = ByteBufCodec::writeUnsignedVarLong;
    ObjLongConsumer<ByteBuf> zigzagWrite = ByteBufCodec::writeVarLong;
    return Stream.of(
        argumentSet("unsigned 300", "ac02", 300L, unsignedRead, unsignedWrite),
        argumentSet("unsigned all bits", "ffffffffffffffffff01", -1L, unsignedRead, unsignedWrite),
        argumentSet("zigzag minus one", "01", -1L, zigzagRead, zigzagWrite),
        argumentSet(
            "zigzag minimum", "ffffffffffffffffff01", Long.MIN_VALUE, zigzagRead, zigzagWrite),
        argumentSet(
            "zigzag maximum", "feffffffffffffffff01", Long.MAX_VALUE, zigzagRead, zigzagWrite));
  }

  static Stream<Arguments> fixedReads() {
    return Stream.of(
        argumentSet("bool", (Consumer<ByteBuf>) ByteBufCodec::readBoolean, 1),
        argumentSet("int8", (Consumer<ByteBuf>) ByteBufCodec::readByte, 1),
        argumentSet("uint8", (Consumer<ByteBuf>) ByteBufCodec::readUnsignedByte, 1),
        argumentSet("int16", (Consumer<ByteBuf>) ByteBufCodec::readShortLE, 2),
        argumentSet("uint16", (Consumer<ByteBuf>) ByteBufCodec::readUnsignedShortLE, 2),
        argumentSet("int32", (Consumer<ByteBuf>) ByteBufCodec::readIntLE, 4),
        argumentSet("int64", (Consumer<ByteBuf>) ByteBufCodec::readLongLE, 8),
        argumentSet("float", (Consumer<ByteBuf>) ByteBufCodec::readFloatLE, 4),
        argumentSet("double", (Consumer<ByteBuf>) ByteBufCodec::readDoubleLE, 8),
        argumentSet("int32 big endian", (Consumer<ByteBuf>) ByteBufCodec::readInt, 4));
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
      String hex, long expected, ToLongFunction<ByteBuf> read, ObjLongConsumer<ByteBuf> write) {
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
    DecodeException error = failure(() -> ByteBufCodec.readUnsignedVarInt(hex("ffffffff10")));
    assertEquals(": out of range at byte 5 of 0", error.getMessage());
  }

  @Test
  void uvarint32WithAContinuationAfterTheFifthByteIsOutOfRange() {
    DecodeException error = failure(() -> ByteBufCodec.readUnsignedVarInt(hex("ffffffff8f00")));
    assertEquals(": out of range at byte 5 of 0", error.getMessage());
  }

  @Test
  void uvarint64PastItsTypeIsOutOfRangeAfterTheTenthByte() {
    DecodeException error =
        failure(() -> ByteBufCodec.readUnsignedVarLong(hex("ffffffffffffffffff02")));
    assertEquals(": out of range at byte 10 of 0", error.getMessage());
  }

  @Test
  void varintThatRunsOutIsTruncatedAtTheEndOfTheInput() {
    DecodeException error = failure(() -> ByteBufCodec.readUnsignedVarInt(hex("8080")));
    assertEquals(": truncated at byte 2 of 0", error.getMessage());
  }

  @Test
  void fixedWidthTruncationReportsTheFieldStart() {
    ByteBuf buf = hex("aabb01020304");
    buf.readerIndex(2);
    DecodeException error = failure(() -> ByteBufCodec.readLongLE(buf));
    assertEquals(": truncated at byte 2 of 0", error.getMessage());
  }

  @ParameterizedTest
  @MethodSource("fixedReads")
  void everyFixedReadOneByteShortIsTruncatedAtTheFieldStart(Consumer<ByteBuf> read, int width) {
    ByteBuf buf = Unpooled.wrappedBuffer(new byte[width - 1]);
    DecodeException error = failure(() -> read.accept(buf));
    assertEquals(": truncated at byte 0 of 0", error.getMessage());
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
    assertEquals(0x04030201, ByteBufCodec.readIntLE(hex("01020304")));
    assertEquals(0x01020304, ByteBufCodec.readInt(hex("01020304")));
  }

  @Test
  void uint8DoesNotSignExtend() {
    assertEquals(255, ByteBufCodec.readUnsignedByte(hex("ff")));
  }

  @Test
  void uint16DoesNotSignExtend() {
    assertEquals(65535, ByteBufCodec.readUnsignedShortLE(hex("ffff")));
  }

  @Test
  void floatReadsLittleEndian() {
    assertEquals(1.0f, ByteBufCodec.readFloatLE(hex("0000803f")));
  }

  @Test
  void doubleReadsLittleEndian() {
    assertEquals(1.0, ByteBufCodec.readDoubleLE(hex("000000000000f03f")));
  }

  @Test
  void boolReadsAnyNonZeroByteAsTrue() {
    assertTrue(ByteBufCodec.readBoolean(hex("02")));
  }

  @ParameterizedTest
  @MethodSource("strings")
  void strReads(String hex, String expected) {
    assertEquals(expected, ByteBufCodec.readString(hex(hex)));
  }

  @ParameterizedTest
  @MethodSource("strings")
  void strWritesWhatItRead(String hex, String value) {
    ByteBuf buf = Unpooled.buffer();
    ByteBufCodec.writeString(buf, value);
    assertEquals(hex, written(buf));
  }

  @Test
  void strLengthPastTheBodyIsTruncatedBeforeAnyAllocation() {
    ByteBuf buf = hex("ffffffff0f");
    DecodeException error = failure(() -> ByteBufCodec.readString(buf));
    assertEquals(": truncated at byte 5 of 0", error.getMessage());
  }

  @Test
  void writingAnUnpairedHighSurrogateIsRejected() {
    ByteBuf buf = Unpooled.buffer();
    IllegalArgumentException error =
        assertThrows(IllegalArgumentException.class, () -> ByteBufCodec.writeString(buf, "\ud800"));
    assertEquals("string has an unpaired surrogate at index 0", error.getMessage());
  }

  @Test
  void rejectedStringLeavesTheBufferEmpty() {
    ByteBuf buf = Unpooled.buffer();
    assertThrows(IllegalArgumentException.class, () -> ByteBufCodec.writeString(buf, "a\udbff"));
    assertEquals(0, buf.readableBytes());
  }

  @Test
  void bytesWriteTheirLengthPrefix() {
    ByteBuf buf = Unpooled.buffer();
    ByteBufCodec.writeByteArray(buf, new byte[] {1, 2, 3});
    assertEquals("03010203", written(buf));
  }

  @Test
  void bytesReadTheirLengthPrefix() {
    assertArrayEquals(new byte[] {1, 2, 3}, ByteBufCodec.readByteArray(hex("03010203")));
  }

  @Test
  void uuidIsTwoLittleEndianLongsMostSignificantFirst() {
    UUID uuid = ByteBufCodec.readUuid(hex("0807060504030201100f0e0d0c0b0a09"));
    assertEquals(new UUID(0x0102030405060708L, 0x090a0b0c0d0e0f10L), uuid);
  }

  @Test
  void uuidWithOnlyTheFirstLongAndAPartIsTruncatedAtTheSecondLong() {
    DecodeException error =
        failure(() -> ByteBufCodec.readUuid(Unpooled.wrappedBuffer(new byte[12])));
    assertEquals(": truncated at byte 8 of 0", error.getMessage());
  }

  @Test
  void uuidWritesMostSignificantLongFirst() {
    ByteBuf buf = Unpooled.buffer();
    ByteBufCodec.writeUuid(buf, new UUID(0x0102030405060708L, 0x090a0b0c0d0e0f10L));
    assertEquals("0807060504030201100f0e0d0c0b0a09", written(buf));
  }

  static Stream<Arguments> bitsets() {
    return Stream.of(
        argumentSet("empty", "00", 30, new BitSet()),
        argumentSet("bit zero", "01", 30, BitSet.valueOf(new long[] {0x01})),
        argumentSet("bit seven", "8001", 30, BitSet.valueOf(new long[] {0x80})),
        argumentSet("bits in two groups", "8101", 30, BitSet.valueOf(new long[] {0x81})),
        argumentSet(
            "last bit of the width", "808080808001", 36, BitSet.valueOf(new long[] {1L << 35})));
  }

  @ParameterizedTest
  @MethodSource("bitsets")
  void bitsetReads(String hex, int width, BitSet expected) {
    assertEquals(expected, ByteBufCodec.readBitSet(hex(hex), width));
  }

  @Test
  void bitsetWritesGroupsUpToTheHighestBit() {
    BitSet bits = new BitSet();
    bits.set(0);
    bits.set(7);
    ByteBuf buf = Unpooled.buffer();
    ByteBufCodec.writeBitSet(buf, bits, 30, "flags");
    assertEquals("8101", written(buf));
  }

  @Test
  void emptyBitsetWritesOneGroup() {
    ByteBuf buf = Unpooled.buffer();
    ByteBufCodec.writeBitSet(buf, new BitSet(), 30, "flags");
    assertEquals("00", written(buf));
  }

  @Test
  void bitsetBitAtTheWidthIsOutOfRange() {
    DecodeException error = failure(() -> ByteBufCodec.readBitSet(hex("08"), 3));
    assertEquals(": out of range at byte 1 of 0", error.getMessage());
  }

  @Test
  void bitsetContinuationIntoAGroupAtTheWidthIsOutOfRange() {
    DecodeException error = failure(() -> ByteBufCodec.readBitSet(hex("8000"), 7));
    assertEquals(": out of range at byte 1 of 0", error.getMessage());
  }

  @Test
  void bitsetThatRunsOutIsTruncated() {
    DecodeException error = failure(() -> ByteBufCodec.readBitSet(hex("80"), 30));
    assertEquals(": truncated at byte 1 of 0", error.getMessage());
  }

  @Test
  void bitsetPastItsWidthIsRejectedOnEncode() {
    BitSet bits = new BitSet();
    bits.set(5);
    IllegalStateException error =
        assertThrows(
            IllegalStateException.class,
            () -> ByteBufCodec.writeBitSet(Unpooled.buffer(), bits, 5, "Pack.flags"));
    assertEquals("Pack.flags: bit 5 is past the width 5", error.getMessage());
  }

  @Test
  void strOrderPutsASupplementaryCharacterAfterAHighBmpOne() {
    assertTrue(ByteBufCodec.STR_ORDER.compare("\uffff", "\ud800\udc00") < 0);
    assertTrue("\uffff".compareTo("\ud800\udc00") > 0);
  }

  @Test
  void strOrderPutsAnEscapedByteBeforeALetterWithAccent() {
    assertTrue(ByteBufCodec.STR_ORDER.compare("\udc80", "é") < 0);
    assertTrue("\udc80".compareTo("é") > 0);
  }

  @Test
  void strOrderTreatsAPrefixAsSmaller() {
    assertTrue(ByteBufCodec.STR_ORDER.compare("ab", "abc") < 0);
  }

  @Test
  void packColorOrdersAlphaRedGreenBlueFromTheTopByte() {
    assertEquals(0xFFBF3F00, ByteBufCodec.packColor(1.0f, 0.75f, 0.25f, 0.0f, "P.c"));
  }

  @Test
  void packColorTruncatesAChannelTowardZero() {
    assertEquals(0x7F, ByteBufCodec.packColor(0.0f, 0.0f, 0.0f, 0.5f, "P.c"));
  }

  static Stream<Arguments> colorChannelsOutOfRange() {
    return Stream.of(
        argumentSet("alpha below zero", -0.5f, 0.0f, 0.0f, 0.0f, "P.c: -0.5 is out of range"),
        argumentSet("red above one", 0.0f, 1.5f, 0.0f, 0.0f, "P.c: 1.5 is out of range"),
        argumentSet("green not a number", 0.0f, 0.0f, Float.NaN, 0.0f, "P.c: NaN is out of range"),
        argumentSet("blue above one", 0.0f, 0.0f, 0.0f, 2.0f, "P.c: 2.0 is out of range"));
  }

  @ParameterizedTest
  @MethodSource("colorChannelsOutOfRange")
  void packColorRejectsAChannelOutsideZeroToOne(
      float alpha, float red, float green, float blue, String message) {
    IllegalArgumentException error =
        assertThrows(
            IllegalArgumentException.class,
            () -> ByteBufCodec.packColor(alpha, red, green, blue, "P.c"));
    assertEquals(message, error.getMessage());
  }

  static Stream<Arguments> colorTexts() {
    return Stream.of(
        argumentSet("hex digits", "#ff00ff00", 0xFF00FF00),
        argumentSet("any first character", "fff", 0xFF),
        argumentSet("a multi-byte first character", "éff", 0),
        argumentSet("leading whitespace", "# \t\n\u000b\f\rff", 0xFF),
        argumentSet("whitespace after the sign", "#- ff", 0),
        argumentSet("plus sign", "#+ff", 0xFF),
        argumentSet("minus sign", "#-ff", 0xFFFFFF01),
        argumentSet("lower-case 0x", "#0xff", 0xFF),
        argumentSet("upper-case 0X", "#0Xff", 0xFF),
        argumentSet("0x without a hex digit", "#0xg", 0),
        argumentSet("digits up to the first other character", "#ffzz1", 0xFF),
        argumentSet("no digits", "#g", 0),
        argumentSet("the first character alone", "#", 0),
        argumentSet("empty text", "", 0),
        argumentSet("leading zeros", "#00000000000000000000ff", 0xFF),
        argumentSet("past 32 bits", "#100000000", 0xFFFFFFFF),
        argumentSet("negated to the top 32 bits", "#-100000000", 0),
        argumentSet("negated to just below the top 32 bits", "#-100000001", 0xFFFFFFFF),
        argumentSet("past 64 bits", "#10000000000000000", 0xFFFFFFFF),
        argumentSet("negated past 64 bits", "#-10000000000000000", 0xFFFFFFFF));
  }

  @ParameterizedTest
  @MethodSource("colorTexts")
  void parseColorReadsTheHexAfterTheFirstByteAsStrtoullDoes(String text, int expected) {
    assertEquals(expected, ByteBufCodec.parseColor(text.getBytes(StandardCharsets.UTF_8)));
  }

  @Test
  void foldAsciiLowersLettersOnly() {
    assertEquals("abc_1", ByteBufCodec.foldAscii("AbC_1"));
  }

  @Test
  void foldAsciiLeavesTheKelvinSignAlone() {
    assertEquals("\u212a", ByteBufCodec.foldAscii("\u212a"));
  }

  @Test
  void decodeReturnsTheValue() {
    int value = ByteBufCodec.decode(hex("2a"), "T", b -> ByteBufCodec.readUnsignedByte(b));
    assertEquals(42, value);
  }

  @Test
  void decodeConsumesTheInput() {
    ByteBuf buf = hex("2a");
    ByteBufCodec.decode(buf, "T", b -> ByteBufCodec.readUnsignedByte(b));
    assertEquals(0, buf.readableBytes());
  }

  @Test
  void decodeReportsTrailingBytesAtTheEndOfTheValue() {
    ByteBuf buf = hex("2a0000");
    DecodeException error =
        assertThrows(
            DecodeException.class,
            () ->
                ByteBufCodec.decode(
                    buf, "PlayStatusPacket", b -> ByteBufCodec.readUnsignedByte(b)));
    assertEquals("PlayStatusPacket: trailing bytes at byte 1 of 3", error.getMessage());
  }

  @Test
  void decodeRestoresTheReaderIndexOnFailure() {
    ByteBuf buf = hex("ff2a0000");
    buf.readerIndex(1);
    assertThrows(
        DecodeException.class,
        () -> ByteBufCodec.decode(buf, "T", b -> ByteBufCodec.readLongLE(b)));
    assertEquals(1, buf.readerIndex());
  }

  @Test
  void decodeStampsTheTypeAndCountsFromTheFirstByteHandedIn() {
    ByteBuf buf = hex("ff0102");
    buf.readerIndex(1);
    DecodeException error =
        assertThrows(
            DecodeException.class,
            () -> ByteBufCodec.decode(buf, "PlayStatusPacket", b -> ByteBufCodec.readIntLE(b)));
    assertEquals("PlayStatusPacket: truncated at byte 0 of 2", error.getMessage());
  }

  static Stream<Arguments> countReads() {
    ToLongFunction<ByteBuf> uvarint32 = ByteBufCodec::readUvarint32Count;
    ToLongFunction<ByteBuf> uint32 = ByteBufCodec::readUint32Count;
    ToLongFunction<ByteBuf> uint16 = ByteBufCodec::readUint16Count;
    ToLongFunction<ByteBuf> varint32 = ByteBufCodec::readVarint32Count;
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
  void negativeCountIsOutOfRangeWhenNarrowed() {
    ByteBuf buf = hex("01");
    long count = ByteBufCodec.readVarint32Count(buf);
    DecodeException error = failure(() -> ByteBufCodec.toCount(buf, count));
    assertEquals(": out of range at byte 1 of 0", error.getMessage());
  }

  @Test
  void countPastIntMaxIsOutOfRangeWhenNarrowed() {
    DecodeException error = failure(() -> ByteBufCodec.toCount(hex("00"), Integer.MAX_VALUE + 1L));
    assertEquals(": out of range at byte 0 of 0", error.getMessage());
  }

  @Test
  void toCountReturnsTheCount() {
    assertEquals(3, ByteBufCodec.toCount(hex("00"), 3));
  }

  @Test
  void negativeCountFactorIsOutOfRange() {
    DecodeException error = failure(() -> ByteBufCodec.countValue(hex("00"), -1));
    assertEquals(": out of range at byte 0 of 0", error.getMessage());
  }

  @Test
  void negativeFactorInAProductIsOutOfRange() {
    DecodeException error = failure(() -> ByteBufCodec.countProduct(hex("00"), 4, -1));
    assertEquals(": out of range at byte 0 of 0", error.getMessage());
  }

  @Test
  void productPastSixtyFourBitsIsOutOfRange() {
    DecodeException error = failure(() -> ByteBufCodec.countProduct(hex("00"), 1L << 32, 1L << 32));
    assertEquals(": out of range at byte 0 of 0", error.getMessage());
  }

  @Test
  void productIsNarrowedAsALong() {
    ByteBuf buf = hex("00");
    long count = ByteBufCodec.countProduct(buf, 65_536, 65_536);
    DecodeException error = failure(() -> ByteBufCodec.toCount(buf, count));
    assertEquals(": out of range at byte 0 of 0", error.getMessage());
  }

  @Test
  void primitiveArrayThatRunsShortIsTruncatedAtTheFirstElementThatDoesNotFit() {
    ByteBuf buf = Unpooled.wrappedBuffer(new byte[10]);
    DecodeException error = failure(() -> ByteBufCodec.needElements(buf, 3, 4));
    assertEquals("[2]: truncated at byte 8 of 0", error.getMessage());
  }

  @Test
  void primitiveArrayThatRunsShortNamesTheElementIndex() {
    ByteBuf buf = Unpooled.wrappedBuffer(new byte[10]);
    DecodeException error = failure(() -> ByteBufCodec.needElements(buf, 3, 4));
    assertEquals(List.of(2), error.getPath());
  }

  @Test
  void primitiveArrayThatFitsIsAccepted() {
    ByteBuf buf = Unpooled.wrappedBuffer(new byte[12]);
    assertDoesNotThrow(() -> ByteBufCodec.needElements(buf, 3, 4));
  }

  @Test
  void initialCapacityOfAHostileCountIsCapped() {
    ByteBuf buf = hex("c0843d");
    int count = ByteBufCodec.toCount(buf, ByteBufCodec.readUvarint32Count(buf));
    assertEquals(65_536, ByteBufCodec.initialCapacity(count));
  }

  @Test
  void initialCapacityKeepsASmallCount() {
    assertEquals(3, ByteBufCodec.initialCapacity(3));
  }
}
