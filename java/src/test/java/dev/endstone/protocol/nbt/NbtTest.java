package dev.endstone.protocol.nbt;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import dev.endstone.protocol.ByteBufCodec;
import dev.endstone.protocol.DecodeException;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

final class NbtTest {
    static Stream<Arguments> payloads() {
        return Stream.of(
                argumentSet("byte", ByteTag.valueOf((byte) 5), "05"),
                argumentSet("byte high bit", ByteTag.valueOf((byte) 254), "fe"),
                argumentSet("short", ShortTag.valueOf((short) -2), "feff"),
                argumentSet("int", IntTag.valueOf(-1), "01"),
                argumentSet("int two groups", IntTag.valueOf(300), "d804"),
                argumentSet("long", LongTag.valueOf(-2L), "03"),
                argumentSet("float", FloatTag.valueOf(1.0f), "0000803f"),
                argumentSet("double", DoubleTag.valueOf(1.0), "000000000000f03f"),
                argumentSet("string", StringTag.valueOf("hi"), "026869"),
                argumentSet("byte array", new ByteArrayTag(new byte[] {1, 2}), "040102"),
                argumentSet(
                        "byte array high bit",
                        new ByteArrayTag(new byte[] {(byte) 254, (byte) 255}),
                        "04feff"),
                argumentSet("int array", new IntArrayTag(new int[] {1, -1}), "040201"),
                argumentSet("list", new ListTag(List.of(IntTag.valueOf(1))), "030202"),
                argumentSet("empty list", new ListTag(), "0000"),
                argumentSet(
                        "compound",
                        compound(Map.of("b", ByteTag.valueOf((byte) 1), "a", IntTag.valueOf(1))),
                        "030161020101620100"));
    }

    static Stream<Arguments> unknownValues() {
        return Stream.of(
                argumentSet("list element type past int array", "0c00", 2),
                argumentSet("list of end with an element", "0002", 2));
    }

    static Stream<Arguments> equalArrays() {
        return Stream.of(
                argumentSet(
                        "byte arrays",
                        new ByteArrayTag(new byte[] {1, 2}),
                        new ByteArrayTag(new byte[] {1, 2})),
                argumentSet(
                        "int arrays",
                        new IntArrayTag(new int[] {1, 2}),
                        new IntArrayTag(new int[] {1, 2})));
    }

    private static CompoundTag compound(Map<String, Tag> entries) {
        CompoundTag tag = new CompoundTag();
        entries.forEach(tag::put);
        return tag;
    }

    private static ByteBuf hex(String hex) {
        return Unpooled.wrappedBuffer(ByteBufUtil.decodeHexDump(hex));
    }

    private static CompoundTag decodeRoot(String hex) {
        return ByteBufCodec.decode(hex(hex), "CompoundTag", ByteBufCodec::readCompoundTag);
    }

    private static DecodeException failRoot(String hex) {
        return assertThrows(DecodeException.class, () -> decodeRoot(hex));
    }

    @ParameterizedTest
    @MethodSource("payloads")
    void encodeWritesThePayload(Tag tag, String hex) {
        ByteBuf buf = Unpooled.buffer();
        tag.encode(buf);
        assertEquals(hex, ByteBufUtil.hexDump(buf));
    }

    @ParameterizedTest
    @MethodSource("payloads")
    void typeDecodesThePayload(Tag tag, String hex) {
        Tag read = ByteBufCodec.decode(hex(hex), "Tag", tag.getType()::decode);
        assertEquals(tag, read);
    }

    @Test
    void ioEncodeWritesTheTypeAnEmptyNameAndThePayload() {
        ByteBuf buf = Unpooled.buffer();
        ByteBufCodec.writeCompoundTag(buf, compound(Map.of("a", IntTag.valueOf(1))));
        assertEquals("0a000301610200", ByteBufUtil.hexDump(buf));
    }

    @Test
    void ioDecodeDropsTheRootName() {
        assertEquals(compound(Map.of("a", IntTag.valueOf(1))), decodeRoot("0a036162630301610200"));
    }

    @Test
    void compoundTypeDecodesTheBarePayload() {
        assertEquals(
                compound(Map.of("a", IntTag.valueOf(1))),
                ByteBufCodec.decode(hex("0301610200"), "CompoundTag", CompoundTag.TYPE::decode));
    }

    @Test
    void compoundKeysAreWrittenInUnsignedByteOrder() {
        ByteBuf buf = Unpooled.buffer();
        compound(
                        Map.of(
                                "\ud800\udc00",
                                ByteTag.valueOf((byte) 0),
                                "\uffff",
                                ByteTag.valueOf((byte) 0)))
                .encode(buf);
        assertEquals("0103efbfbf000104f09080800000", ByteBufUtil.hexDump(buf));
    }

    @Test
    void stringAndArrayTagsRejectNull() {
        assertEquals(
                "StringTag.value",
                assertThrows(NullPointerException.class, () -> new StringTag(null)).getMessage());
        assertEquals(
                "ByteArrayTag.data",
                assertThrows(NullPointerException.class, () -> new ByteArrayTag(null))
                        .getMessage());
        assertEquals(
                "IntArrayTag.data",
                assertThrows(NullPointerException.class, () -> new IntArrayTag(null)).getMessage());
    }

    @Test
    void aDuplicateKeyKeepsTheFirstValue() {
        assertEquals(
                compound(Map.of("a", ByteTag.valueOf((byte) 1))),
                decodeRoot("0a00010161010101610200"));
    }

    @Test
    void anUnknownTagIdInACompoundIsAnUnknownValue() {
        DecodeException error = failRoot("0a000c");
        assertEquals("CompoundTag: unknown value at byte 3 of 3", error.getMessage());
    }

    @Test
    void aRootThatIsNotACompoundIsAnUnknownValue() {
        DecodeException error = failRoot("010005");
        assertEquals("CompoundTag: unknown value at byte 3 of 3", error.getMessage());
    }

    @Test
    void anEndRootIsAnUnknownValue() {
        DecodeException error = failRoot("00");
        assertEquals("CompoundTag: unknown value at byte 1 of 1", error.getMessage());
    }

    @ParameterizedTest
    @MethodSource("unknownValues")
    void aBadListHeaderIsAnUnknownValue(String hex, int offset) {
        DecodeException error =
                assertThrows(
                        DecodeException.class,
                        () -> ByteBufCodec.decode(hex(hex), "Tag", ListTag.TYPE::decode));
        assertEquals("Tag: unknown value at byte " + offset + " of 2", error.getMessage());
    }

    @Test
    void aNegativeByteArrayLengthIsOutOfRange() {
        DecodeException error = failRoot("0a000701610100");
        assertEquals("CompoundTag: out of range at byte 6 of 7", error.getMessage());
    }

    @Test
    void aByteArrayLengthPastTheBodyIsTruncated() {
        DecodeException error = failRoot("0a000701610a");
        assertEquals("CompoundTag: truncated at byte 6 of 6", error.getMessage());
    }

    @ParameterizedTest
    @MethodSource("equalArrays")
    void arrayTagsCompareByContent(Tag a, Tag b) {
        assertEquals(a, b);
    }

    @Test
    void arrayTagsWithDifferentContentDiffer() {
        assertNotEquals(new IntArrayTag(new int[] {1}), new IntArrayTag(new int[] {2}));
    }

    @Test
    void aListRejectsAnElementOfAnotherType() {
        IllegalArgumentException error =
                assertThrows(
                        IllegalArgumentException.class,
                        () -> new ListTag(Tag.TAG_INT, List.of(ByteTag.valueOf((byte) 1))));
        assertEquals("ListTag.element: tag 1 in a list of tag 3", error.getMessage());
    }

    @Test
    void anEmptyListKeepsItsElementType() {
        ByteBuf buf = Unpooled.buffer();
        new ListTag(Tag.TAG_INT, List.of()).encode(buf);
        assertEquals("0300", ByteBufUtil.hexDump(buf));
    }

    @Test
    void getIntOrConvertsANumericTagAndFallsBackOtherwise() {
        CompoundTag tag = compound(Map.of("a", ByteTag.valueOf((byte) 7)));
        assertEquals(7, tag.getIntOr("a", 0));
        assertEquals(9, tag.getIntOr("b", 9));
    }

    @Test
    void compoundTagDataWritesThePayloadWithoutARoot() {
        ByteBuf buf = Unpooled.buffer();
        ByteBufCodec.writeCompoundTagData(
                buf, new CompoundTagData(compound(Map.of("a", IntTag.valueOf(1)))));
        assertEquals("03016102" + "00", ByteBufUtil.hexDump(buf));
    }

    @Test
    void compoundTagDataReadsThePayloadWithoutARoot() {
        assertEquals(
                new CompoundTagData(compound(Map.of("a", IntTag.valueOf(1)))),
                ByteBufCodec.decode(
                        hex("0301610200"), "CompoundTagData", ByteBufCodec::readCompoundTagData));
    }

    @Test
    void compoundTagDataCopiesTheTag() {
        CompoundTagData data = new CompoundTagData(compound(Map.of("a", IntTag.valueOf(1))));
        assertNotSame(data.tag(), data.copy().tag());
    }

    @Test
    void compoundTagDefaultInstanceIsNeverShared() {
        assertNotSame(CompoundTag.getDefaultInstance(), CompoundTag.getDefaultInstance());
    }

    @Test
    void compoundTagDataDefaultInstanceHoldsAnEmptyCompound() {
        assertEquals(new CompoundTagData(new CompoundTag()), CompoundTagData.getDefaultInstance());
    }
}
