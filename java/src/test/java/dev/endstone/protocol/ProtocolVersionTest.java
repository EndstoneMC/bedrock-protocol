package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import org.junit.jupiter.api.Test;

final class ProtocolVersionTest {
    @Test
    void aNumberAfterASnapshotSharesItsSnapshot() {
        assertEquals(2168, ProtocolVersion.of(2169).orElseThrow().snapshot());
    }

    @Test
    void aReleaseInsideARangeFindsTheRange() {
        assertEquals(2225, ProtocolVersion.of("1.26.63").orElseThrow().number());
    }

    @Test
    void anUnknownNumberIsEmpty() {
        assertTrue(ProtocolVersion.of(1).isEmpty());
    }

    @Test
    void aMalformedReleaseIsEmpty() {
        assertTrue(ProtocolVersion.of("1.26").isEmpty());
    }

    @Test
    void aSnapshotNumberDecodesWithItsSnapshotsClasses() {
        Packet packet =
                ProtocolVersion.of(2169)
                        .orElseThrow()
                        .decodePacket(
                                PlaySoundPacket.ID,
                                Unpooled.wrappedBuffer(
                                        ByteBufUtil.decodeHexDump(
                                                "01610204060000803f0000803f0000")));
        assertEquals(dev.endstone.protocol.v2168.PlaySoundPacket.class, packet.getClass());
    }

    @Test
    void aSnapshotNumberEncodesWithItsSnapshotsClasses() {
        ProtocolVersion version = ProtocolVersion.of(2169).orElseThrow();
        ByteBuf buf = Unpooled.buffer();
        version.encodePacket(
                dev.endstone.protocol.v2168.PlaySoundPacket.newBuilder()
                        .setName("a")
                        .setPos(BlockPos.newBuilder().setX(1).setY(2).setZ(3).build())
                        .setVolume(1f)
                        .setPitch(1f)
                        .build(),
                buf);
        assertEquals("01610204060000803f0000803f0000", ByteBufUtil.hexDump(buf));
    }

    @Test
    void encodingAPacketOfAnotherProtocolIsRejected() {
        ProtocolVersion version = ProtocolVersion.of(2225).orElseThrow();
        Packet packet = dev.endstone.protocol.v2168.PlaySoundPacket.getDefaultInstance();
        ByteBuf buf = Unpooled.buffer();
        IllegalArgumentException thrown =
                assertThrows(
                        IllegalArgumentException.class, () -> version.encodePacket(packet, buf));
        assertEquals(
                "packet: dev.endstone.protocol.v2168.PlaySoundPacket "
                        + "is not a packet at protocol 2225",
                thrown.getMessage());
    }
}
