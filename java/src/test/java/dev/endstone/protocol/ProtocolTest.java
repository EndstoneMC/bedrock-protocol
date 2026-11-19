package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.netty.buffer.ByteBufUtil;
import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;

final class ProtocolTest {
    private static final TextPacket HELLO =
            TextPacket.newBuilder()
                    .setMessageOnly(
                            TextPacket.MessageOnly.newBuilder()
                                    .setType(TextPacketType.CHAT)
                                    .setMessage("hello")
                                    .build())
                    .build();

    private static final dev.endstone.protocol.v2168.PlaySoundPacket SOUND =
            dev.endstone.protocol.v2168.PlaySoundPacket.newBuilder()
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

    @ParameterizedTest
    @EnumSource(Protocol.class)
    void aConstantIsNamedAfterItsVersion(Protocol protocol) {
        assertEquals("v" + protocol.version(), protocol.name());
    }

    @ParameterizedTest
    @EnumSource(Protocol.class)
    void aConstantsVersionIsSupported(Protocol protocol) {
        assertTrue(ProtocolVersion.get(protocol.version()).isPresent());
    }

    @Test
    void theConstantsAscend() {
        List<Integer> versions = Arrays.stream(Protocol.values()).map(Protocol::version).toList();
        assertEquals(versions.stream().sorted().toList(), versions);
    }

    @Test
    void latestIsTheLastConstant() {
        assertEquals(Protocol.values()[Protocol.values().length - 1], Protocol.latest());
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
                "v2168.PlaySoundPacket: is not a type at protocol 2225",
                assertThrows(IllegalArgumentException.class, () -> Protocol.v2225.encode(SOUND))
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
                        dev.endstone.protocol.v2168.PlaySoundPacket.class,
                        bytes("01610204060000803f0000803f0000")));
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
