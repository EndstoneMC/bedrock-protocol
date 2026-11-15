package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;

import dev.endstone.protocol.nbt.CompoundTag;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import org.junit.jupiter.api.Test;

final class MessageTest {
    private static final ProtocolVersion LATEST =
            ProtocolVersion.of(ProtocolVersion.LATEST_VERSION).orElseThrow();

    private static ByteBuf hex(String hex) {
        return Unpooled.wrappedBuffer(ByteBufUtil.decodeHexDump(hex));
    }

    private static String encoded(Packet packet) {
        ByteBuf buf = Unpooled.buffer();
        LATEST.encodePacket(packet, buf);
        return ByteBufUtil.hexDump(buf);
    }

    private static DecodeException failure(int packetId, String hex) {
        return assertThrows(DecodeException.class, () -> LATEST.decodePacket(packetId, hex(hex)));
    }

    @Test
    void truncatedInputNamesTheFieldThatFailed() {
        assertEquals(
                "ToastRequestPacket.content: truncated at byte 3 of 3",
                failure(ToastRequestPacket.ID, "026162").getMessage());
    }

    @Test
    void truncatedInputKeepsTheFieldsBeforeTheCut() {
        ToastRequestPacket unfinished =
                assertInstanceOf(
                        ToastRequestPacket.class,
                        failure(ToastRequestPacket.ID, "026162").getUnfinishedMessage());
        assertEquals("ab", unfinished.getTitle());
    }

    @Test
    void truncatedInputLeavesTheFieldsAfterTheCutAtTheirDefaults() {
        ToastRequestPacket unfinished =
                assertInstanceOf(
                        ToastRequestPacket.class,
                        failure(ToastRequestPacket.ID, "026162").getUnfinishedMessage());
        assertEquals("", unfinished.getContent());
    }

    @Test
    void aNarrowSetterRejectsAValueItCannotHold() {
        ActorPickRequestPacket.Builder builder = ActorPickRequestPacket.newBuilder();
        assertEquals(
                "ActorPickRequestPacket.maxSlots: cannot hold 256",
                assertThrows(IllegalArgumentException.class, () -> builder.setMaxSlots(256))
                        .getMessage());
    }

    @Test
    void anUnknownUnionIndexIsAnUnknownValue() {
        assertEquals(
                "TextPacket.body: unknown value at byte 2 of 2",
                failure(TextPacket.ID, "0009").getMessage());
    }

    @Test
    void clearingARequiredUnionRestoresItsFirstCase() {
        TextPacket.Builder builder =
                TextPacket.newBuilder()
                        .setAuthorAndMessage(TextPacket.AuthorAndMessage.getDefaultInstance())
                        .clearBody();
        assertEquals(TextPacket.BodyCase.MESSAGE_ONLY, builder.getBodyCase());
    }

    @Test
    void anUnknownEnumNumberDecodesToUnrecognized() {
        PlayStatusPacket packet =
                assertInstanceOf(
                        PlayStatusPacket.class,
                        LATEST.decodePacket(PlayStatusPacket.ID, hex("000003e7")));
        assertEquals(PlayStatus.UNRECOGNIZED, packet.getStatus());
    }

    @Test
    void anUnknownEnumNumberKeepsItsNumber() {
        PlayStatusPacket packet =
                assertInstanceOf(
                        PlayStatusPacket.class,
                        LATEST.decodePacket(PlayStatusPacket.ID, hex("000003e7")));
        assertEquals(999, packet.getStatusValue());
    }

    @Test
    void anUnknownEnumNumberReEncodesAsItself() {
        assertEquals(
                "000003e7", encoded(LATEST.decodePacket(PlayStatusPacket.ID, hex("000003e7"))));
    }

    @Test
    void aPacketIdAddedAfterAVersionDecodesToItsConstantAtThatVersion() {
        PacketViolationWarningPacket packet =
                assertInstanceOf(
                        PacketViolationWarningPacket.class,
                        ProtocolVersion.of(729)
                                .orElseThrow()
                                .decodePacket(PacketViolationWarningPacket.ID, hex("0000940500")));
        assertEquals(MinecraftPacketIds.CLIENTBOUND_DATA_STORE, packet.getViolatingPacketId());
    }

    @Test
    void aPacketIdAddedAfterAVersionEncodesAsItselfAtThatVersion() {
        ProtocolVersion version = ProtocolVersion.of(729).orElseThrow();
        ByteBuf buf = Unpooled.buffer();
        version.encodePacket(
                PacketViolationWarningPacket.newBuilder()
                        .setViolatingPacketId(MinecraftPacketIds.CLIENTBOUND_DATA_STORE)
                        .build(),
                buf);
        assertEquals("0000940500", ByteBufUtil.hexDump(buf));
    }

    @Test
    void theDefaultInstanceEncodesLikeAnEmptyBuilder() {
        assertEquals(
                encoded(ToastRequestPacket.newBuilder().build()),
                encoded(ToastRequestPacket.getDefaultInstance()));
    }

    @Test
    void aGetterOnACompoundTagReturnsACopy() {
        AvailableActorIdentifiersPacket packet =
                assertInstanceOf(
                        AvailableActorIdentifiersPacket.class,
                        LATEST.decodePacket(AvailableActorIdentifiersPacket.ID, hex("0a0000")));
        CompoundTag copy = packet.getIdentifierList();
        copy.putInt("x", 1);
        assertFalse(packet.getIdentifierList().contains("x"));
    }

    @Test
    void anUnknownPacketIdIsAnUnknownValue() {
        assertEquals(
                "PacketHeader.packet_id: unknown value at byte 0 of 2",
                failure(1023, "0000").getMessage());
    }
}
