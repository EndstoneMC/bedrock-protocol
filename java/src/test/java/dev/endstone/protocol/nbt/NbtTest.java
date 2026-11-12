package dev.endstone.protocol.nbt;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import dev.endstone.protocol.DecodeBudget;
import dev.endstone.protocol.DecodeException;
import dev.endstone.protocol.DecodeException.Reason;
import dev.endstone.protocol.DecodeLimits;
import dev.endstone.protocol.Wire;
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

class NbtTest {
    static Stream<Arguments> payloads() {
        return Stream.of(
                argumentSet("byte", new ByteTag((byte) 5), "05"),
                argumentSet("short", new ShortTag((short) -2), "feff"),
                argumentSet("int", new IntTag(-1), "01"),
                argumentSet("int two groups", new IntTag(300), "d804"),
                argumentSet("int64", new Int64Tag(-2L), "03"),
                argumentSet("float", new FloatTag(1.0f), "0000803f"),
                argumentSet("double", new DoubleTag(1.0), "000000000000f03f"),
                argumentSet("string", new StringTag("hi"), "026869"),
                argumentSet("byte array", new ByteArrayTag(new byte[] {1, 2}), "040102"),
                argumentSet("int array", new IntArrayTag(new int[] {1, -1}), "040201"),
                argumentSet("list", new ListTag(TagType.INT, List.of(new IntTag(1))), "030202"),
                argumentSet("empty list", new ListTag(TagType.END, List.of()), "0000"),
                argumentSet(
                        "compound",
                        new CompoundTag(Map.of("b", new ByteTag((byte) 1), "a", new IntTag(1))),
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

    private static ByteBuf hex(String hex) {
        return Unpooled.wrappedBuffer(ByteBufUtil.decodeHexDump(hex));
    }

    private static CompoundTag decodeRoot(String hex) {
        return Wire.decode(hex(hex), DecodeLimits.DEFAULT, "CompoundTag", CompoundTag::read);
    }

    private static DecodeException failRoot(String hex) {
        return assertThrows(DecodeException.class, () -> decodeRoot(hex));
    }

    @ParameterizedTest
    @MethodSource("payloads")
    void encodeDataWritesThePayload(Tag tag, String hex) {
        ByteBuf buf = Unpooled.buffer();
        tag.encodeData(buf);
        assertEquals(hex, ByteBufUtil.hexDump(buf));
    }

    @ParameterizedTest
    @MethodSource("payloads")
    void readDataReadsThePayload(Tag tag, String hex) {
        Tag read =
                Wire.decode(
                        hex(hex),
                        DecodeLimits.DEFAULT,
                        "Tag",
                        (buf, budget) -> Tag.readData(buf, budget, tag.type()));
        assertEquals(tag, read);
    }

    @Test
    void encodeWritesTheTypeAnEmptyNameAndThePayload() {
        ByteBuf buf = Unpooled.buffer();
        new CompoundTag(Map.of("a", new IntTag(1))).encode(buf);
        assertEquals("0a000301610200", ByteBufUtil.hexDump(buf));
    }

    @Test
    void readDropsTheRootName() {
        assertEquals(
                new CompoundTag(Map.of("a", new IntTag(1))), decodeRoot("0a036162630301610200"));
    }

    @Test
    void readDataReadsTheBarePayload() {
        assertEquals(
                new CompoundTag(Map.of("a", new IntTag(1))),
                Wire.decode(
                        hex("0301610200"),
                        DecodeLimits.DEFAULT,
                        "CompoundTag",
                        CompoundTag::readData));
    }

    @Test
    void compoundKeysAreWrittenInUnsignedByteOrder() {
        ByteBuf buf = Unpooled.buffer();
        new CompoundTag(Map.of("𐀀", new ByteTag((byte) 0), "￿", new ByteTag((byte) 0)))
                .encodeData(buf);
        assertEquals("0103efbfbf000104f09080800000", ByteBufUtil.hexDump(buf));
    }

    @Test
    void aDuplicateKeyKeepsTheFirstValue() {
        assertEquals(
                new CompoundTag(Map.of("a", new ByteTag((byte) 1))),
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
                        () ->
                                Wire.decode(
                                        hex(hex),
                                        DecodeLimits.DEFAULT,
                                        "Tag",
                                        (buf, budget) -> Tag.readData(buf, budget, TagType.LIST)));
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

    @Test
    void aCompoundNested129DeepIsTooDeep() {
        DecodeException error = failRoot("0a00" + "0a0161".repeat(128) + "00".repeat(129));
        assertEquals("CompoundTag: too deep at byte 386 of 515", error.getMessage());
    }

    @Test
    void aCompoundNested128DeepIsAccepted() {
        assertDoesNotThrow(() -> decodeRoot("0a00" + "0a0161".repeat(127) + "00".repeat(128)));
    }

    @Test
    void entriesPastTheElementLimitAreTooLarge() {
        DecodeBudget budget = new DecodeBudget(new DecodeLimits(1, 1_000L, 128));
        DecodeException error =
                assertThrows(
                        DecodeException.class,
                        () -> CompoundTag.readData(hex("010161010101620100"), budget));
        assertEquals(Reason.TOO_LARGE, error.getReason());
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
                        () -> new ListTag(TagType.INT, List.of(new ByteTag((byte) 1))));
        assertEquals("ListTag.elements: BYTE in a list of INT", error.getMessage());
    }
}
