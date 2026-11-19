package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import dev.endstone.protocol.v2168.PlaySoundPacket_v2168;
import io.netty.buffer.ByteBufUtil;
import java.util.Arrays;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

final class ProtocolTest {
    private static final int LATEST_PROTOCOL =
            Arrays.stream(Protocol.class.getClasses())
                    .mapToInt(pinned -> Integer.parseInt(pinned.getSimpleName().substring(1)))
                    .max()
                    .orElseThrow();

    private static final TextPacket HELLO =
            TextPacket.newBuilder()
                    .setMessageOnly(
                            TextPacket.MessageOnly.newBuilder()
                                    .setType(TextPacketType.CHAT)
                                    .setMessage("hello")
                                    .build())
                    .build();

    private static final PlaySoundPacket_v2168 SOUND =
            PlaySoundPacket_v2168.newBuilder()
                    .setName("a")
                    .setPos(BlockPos.newBuilder().setX(1).setY(2).setZ(3).build())
                    .setVolume(1f)
                    .setPitch(1f)
                    .build();

    private record Unregistered() implements Packet {
        @Override
        public int getPacketId() {
            return 1;
        }
    }

    private static byte[] bytes(String hex) {
        return ByteBufUtil.decodeHexDump(hex);
    }

    private static String hex(byte[] bytes) {
        return ByteBufUtil.hexDump(bytes);
    }

    static Stream<Arguments> pinnedClasses() {
        return Arrays.stream(Protocol.class.getClasses())
                .map(pinned -> argumentSet(pinned.getSimpleName(), pinned));
    }

    @ParameterizedTest
    @MethodSource("pinnedClasses")
    void aPinnedClassIsNamedAfterItsVersion(Class<?> pinned) throws ReflectiveOperationException {
        assertEquals("v" + pinned.getField("VERSION").getInt(null), pinned.getSimpleName());
    }

    @ParameterizedTest
    @MethodSource("pinnedClasses")
    void aPinnedClassesVersionIsSupported(Class<?> pinned) throws ReflectiveOperationException {
        assertTrue(ProtocolVersion.get(pinned.getField("VERSION").getInt(null)).isPresent());
    }

    @Test
    void aValueEncodesToItsBytes() {
        assertEquals("0000010568656c6c6f000000", hex(Protocol.v2225.encode(HELLO)));
    }

    @Test
    void aValueDecodesBackEqualAfterEncoding() {
        assertEquals(HELLO, Protocol.v2225.decode(TextPacket.class, Protocol.v2225.encode(HELLO)));
    }

    @Test
    void decodeRejectsTrailingBytes() {
        assertEquals(
                "TextPacket: trailing bytes at byte 12 of 13",
                assertThrows(
                                DecodeException.class,
                                () ->
                                        Protocol.v2225.decode(
                                                TextPacket.class,
                                                bytes("0000010568656c6c6f000000ff")))
                        .getMessage());
    }

    @Test
    void encodeRejectsAValueOfAnotherProtocol() {
        assertEquals(
                "v2168.PlaySoundPacket_v2168: is not a type at protocol 2225",
                assertThrows(IllegalArgumentException.class, () -> Protocol.v2225.encode(SOUND))
                        .getMessage());
    }

    @Test
    void theBareEncodeIsAtTheLatestProtocol() {
        assertEquals(
                "v2168.PlaySoundPacket_v2168: is not a type at protocol " + LATEST_PROTOCOL,
                assertThrows(IllegalArgumentException.class, () -> Protocol.encode(SOUND))
                        .getMessage());
    }

    @Test
    void theBareDecodeIsAtTheLatestProtocol() {
        assertEquals(
                "v2168.PlaySoundPacket_v2168: is not a type at protocol " + LATEST_PROTOCOL,
                assertThrows(
                                IllegalArgumentException.class,
                                () ->
                                        Protocol.decode(
                                                PlaySoundPacket_v2168.class,
                                                bytes("01610204060000803f0000803f0000")))
                        .getMessage());
    }

    @Test
    void aRedeclaredPacketEncodesWithItsOwnClass() {
        assertEquals("01610204060000803f0000803f0000", hex(Protocol.v2168.encode(SOUND)));
    }

    @Test
    void aRedeclaredPacketDecodesWithItsOwnClass() {
        assertEquals(
                SOUND,
                Protocol.v2168.decode(
                        PlaySoundPacket_v2168.class, bytes("01610204060000803f0000803f0000")));
    }

    @Test
    void encodeRejectsAPacketItDoesNotKnow() {
        assertEquals(
                "dev.endstone.protocol.ProtocolTest$Unregistered: is not a type at protocol 2225",
                assertThrows(
                                IllegalArgumentException.class,
                                () -> Protocol.v2225.encode(new Unregistered()))
                        .getMessage());
    }

    @Test
    void decodeRejectsAPacketItDoesNotKnow() {
        assertEquals(
                "dev.endstone.protocol.ProtocolTest$Unregistered: is not a type at protocol 2225",
                assertThrows(
                                IllegalArgumentException.class,
                                () -> Protocol.v2225.decode(Unregistered.class, new byte[0]))
                        .getMessage());
    }
}
