package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

class PacketHeaderTest {
    static Stream<Arguments> packed() {
        return Stream.of(
                argumentSet("id only", new PacketHeader(9, 0, 0), "09"),
                argumentSet("largest id", new PacketHeader(0x3FF, 0, 0), "ff07"),
                argumentSet("recipient", new PacketHeader(1, 3, 0), "8118"),
                argumentSet("sender", new PacketHeader(1, 0, 2), "8140"),
                argumentSet("all fields", new PacketHeader(0x3FF, 3, 3), "ff7f"));
    }

    static Stream<Arguments> outOfRange() {
        return Stream.of(
                argumentSet("id", 1024, 0, 0, "PacketHeader.packetId: cannot hold 1024"),
                argumentSet("negative id", -1, 0, 0, "PacketHeader.packetId: cannot hold -1"),
                argumentSet("recipient", 0, 4, 0, "PacketHeader.recipientSubId: cannot hold 4"),
                argumentSet("sender", 0, 0, 4, "PacketHeader.senderSubId: cannot hold 4"));
    }

    private static ByteBuf hex(String hex) {
        return Unpooled.wrappedBuffer(ByteBufUtil.decodeHexDump(hex));
    }

    @ParameterizedTest
    @MethodSource("packed")
    void encodePacksTheFields(PacketHeader header, String hex) {
        ByteBuf buf = Unpooled.buffer();
        header.encode(buf);
        assertEquals(hex, ByteBufUtil.hexDump(buf));
    }

    @ParameterizedTest
    @MethodSource("packed")
    void decodeUnpacksTheFields(PacketHeader header, String hex) {
        assertEquals(header, PacketHeader.decode(hex(hex)));
    }

    @Test
    void decodeOfNothingIsTruncated() {
        DecodeException error =
                assertThrows(DecodeException.class, () -> PacketHeader.decode(Unpooled.buffer()));
        assertEquals("PacketHeader: truncated at byte 0 of 0", error.getMessage());
    }

    @Test
    void decodeDropsTheBitsPastTheSender() {
        assertEquals(new PacketHeader(0, 0, 0), PacketHeader.decode(hex("808001")));
    }

    @ParameterizedTest
    @MethodSource("outOfRange")
    void constructorRejectsAFieldPastItsBits(
            int packetId, int recipientSubId, int senderSubId, String message) {
        IllegalArgumentException error =
                assertThrows(
                        IllegalArgumentException.class,
                        () -> new PacketHeader(packetId, recipientSubId, senderSubId));
        assertEquals(message, error.getMessage());
    }
}
