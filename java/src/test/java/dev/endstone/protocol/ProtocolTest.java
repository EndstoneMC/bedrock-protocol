package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import java.util.Arrays;
import org.junit.jupiter.api.Test;

final class ProtocolTest {
    private static final TextPacket HELLO =
            TextPacket.newBuilder()
                    .setMessageOnly(
                            TextPacket.MessageOnly.newBuilder()
                                    .setType(TextPacketType.CHAT)
                                    .setMessage("hello")
                                    .build())
                    .build();

    private static final PlayStatusPacket PLAYER_SPAWN =
            PlayStatusPacket.newBuilder().setStatus(PlayStatus.PLAYER_SPAWN).build();

    private static final dev.endstone.protocol.v2168.PlaySoundPacket SOUND =
            dev.endstone.protocol.v2168.PlaySoundPacket.newBuilder()
                    .setName("a")
                    .setPos(BlockPos.newBuilder().setX(1).setY(2).setZ(3).build())
                    .setVolume(1f)
                    .setPitch(1f)
                    .build();

    private static byte[] bytes(String hex) {
        return ByteBufUtil.decodeHexDump(hex);
    }

    private static String hex(byte[] bytes) {
        return ByteBufUtil.hexDump(bytes);
    }

    @Test
    void aNumberAfterASnapshotIsItsSnapshot() {
        assertEquals(Protocol.v2168, Protocol.of(2169).orElseThrow());
    }

    @Test
    void aReleaseInsideARangeIsItsProtocol() {
        assertEquals(Protocol.v2225, Protocol.of("1.26.63").orElseThrow());
    }

    @Test
    void anUnknownNumberHasNoProtocol() {
        assertTrue(Protocol.of(1).isEmpty());
    }

    @Test
    void theConstantsAreTheModelledVersionsInOrder() {
        assertEquals(
                ProtocolVersion.VERSIONS,
                Arrays.stream(Protocol.values()).map(Protocol::version).toList());
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
    void decodeRejectsAUnionWrapper() {
        assertEquals(
                "dev.endstone.protocol.ClientboundDataStorePacket$Updates: "
                        + "is not a type at protocol 2225",
                assertThrows(
                                IllegalArgumentException.class,
                                () ->
                                        Protocol.v2225.decode(
                                                ClientboundDataStorePacket.Updates.class,
                                                new byte[0]))
                        .getMessage());
    }

    @Test
    void encodeRejectsAUnionWrapper() {
        assertEquals(
                "dev.endstone.protocol.ClientboundDataStorePacket$Updates: "
                        + "is not a type at protocol 2225",
                assertThrows(
                                IllegalArgumentException.class,
                                () ->
                                        Protocol.v2225.encode(
                                                ClientboundDataStorePacket.Updates
                                                        .getDefaultInstance()))
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
    void aModeArgumentPicksTheEncoding() {
        assertEquals(
                "0203d804",
                hex(
                        Protocol.v1001.encode(
                                SubChunkPos.newBuilder().setX(1).setY(-2).setZ(300).build(),
                                SerializationMode.MANUAL)));
    }

    @Test
    void aModeArgumentPicksTheDecoding() {
        assertEquals(
                SubChunkPos.newBuilder().setX(1).setY(-2).setZ(300).build(),
                Protocol.v1001.decode(
                        SubChunkPos.class, bytes("0203d804"), SerializationMode.MANUAL));
    }

    @Test
    void aMissingModeIsRejectedWhereNoModeIsTheDefault() {
        assertEquals(
                "SubChunkPos: no default mode at protocol 1001; it has CEREAL and MANUAL",
                assertThrows(
                                IllegalArgumentException.class,
                                () ->
                                        Protocol.v1001.encode(
                                                SubChunkPos.newBuilder()
                                                        .setX(1)
                                                        .setY(-2)
                                                        .setZ(300)
                                                        .build()))
                        .getMessage());
    }

    @Test
    void encodePacketFramesTheBodyWithTheSubIds() {
        assertEquals("824800000003", hex(Protocol.v2225.encodePacket(PLAYER_SPAWN, 1, 2)));
    }

    @Test
    void decodePacketGivesTheHeaderOfTheFrame() {
        assertEquals(
                new PacketHeader(2, 1, 2),
                Protocol.v2225.decodePacket(bytes("824800000003")).header());
    }

    @Test
    void decodePacketGivesThePacketOfTheFrame() {
        assertEquals(PLAYER_SPAWN, Protocol.v2225.decodePacket(bytes("824800000003")).packet());
    }

    @Test
    void decodePacketRejectsAnUnknownPacketId() {
        assertEquals(
                "PacketHeader.packet_id: unknown value at byte 2 of 2",
                assertThrows(
                                DecodeException.class,
                                () -> Protocol.v2225.decodePacket(bytes("ff07")))
                        .getMessage());
    }

    @Test
    void decodePacketRejectsAnEmptyFrame() {
        assertEquals(
                "PacketHeader: truncated at byte 0 of 0",
                assertThrows(DecodeException.class, () -> Protocol.v2225.decodePacket(new byte[0]))
                        .getMessage());
    }

    @Test
    void aTruncatedFramedBodyCountsFromTheHeader() {
        assertEquals(
                "ToastRequestPacket.content: truncated at byte 5 of 5",
                assertThrows(
                                DecodeException.class,
                                () -> Protocol.v2225.decodePacket(bytes("ba01026162")))
                        .getMessage());
    }

    @Test
    void theOffsetCountsFromTheFirstByteDecodePacketIsHanded() {
        ByteBuf buf = Unpooled.wrappedBuffer(bytes("00ba01026162"));
        buf.skipBytes(1);
        assertEquals(
                "ToastRequestPacket.content: truncated at byte 5 of 5",
                assertThrows(DecodeException.class, () -> Protocol.v2225.decodePacket(buf))
                        .getMessage());
    }

    @Test
    void encodePacketRejectsAPacketOfAnotherProtocol() {
        assertEquals(
                "packet: dev.endstone.protocol.v2168.PlaySoundPacket "
                        + "is not a packet at protocol 2225",
                assertThrows(
                                IllegalArgumentException.class,
                                () -> Protocol.v2225.encodePacket(SOUND))
                        .getMessage());
    }

    @Test
    void aSnapshotNumberEncodesWithItsSnapshotsClasses() {
        assertEquals(
                "01610204060000803f0000803f0000",
                hex(Protocol.of(2169).orElseThrow().encode(SOUND)));
    }

    @Test
    void aSnapshotNumberDecodesWithItsSnapshotsClasses() {
        assertEquals(
                dev.endstone.protocol.v2168.PlaySoundPacket.class,
                Protocol.of(2169)
                        .orElseThrow()
                        .decodePacket(bytes("5601610204060000803f0000803f0000"))
                        .packet()
                        .getClass());
    }
}
