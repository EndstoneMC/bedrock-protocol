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

    private static final ProtocolVersion EARLY = ProtocolVersion.of(729).orElseThrow();

    private static String animate(String version) {
        return "000000" + version + "00" + "00000000" + "00";
    }

    private static String encodedAt(ProtocolVersion version, Packet packet) {
        ByteBuf buf = Unpooled.buffer();
        version.encodePacket(packet, buf);
        return ByteBufUtil.hexDump(buf);
    }

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
    void aPacketIdAddedAfterAVersionFailsToDecodeAtThatVersion() {
        assertEquals(
                "PacketViolationWarningPacket.violating_packet_id: unknown value at byte 4 of 5",
                assertThrows(
                                DecodeException.class,
                                () ->
                                        EARLY.decodePacket(
                                                PacketViolationWarningPacket.ID, hex("0000940500")))
                        .getMessage());
    }

    @Test
    void aPacketIdAddedAfterAVersionFailsToEncodeAtThatVersion() {
        assertEquals(
                "MinecraftPacketIds: 330 has no number at protocol 729",
                assertThrows(
                                IllegalArgumentException.class,
                                () ->
                                        EARLY.encodePacket(
                                                PacketViolationWarningPacket.newBuilder()
                                                        .setViolatingPacketId(
                                                                MinecraftPacketIds
                                                                        .CLIENTBOUND_DATA_STORE)
                                                        .build(),
                                                Unpooled.buffer()))
                        .getMessage());
    }

    @Test
    void theLatestMolangVersionEncodesAsTheNumberItHasAtAnEarlyVersion() {
        assertEquals(
                animate("0c000000"),
                encodedAt(
                        EARLY,
                        AnimateEntityPacket.newBuilder()
                                .setStopExpressionVersion(MolangVersion.LATEST)
                                .build()));
    }

    @Test
    void theLatestMolangVersionEncodesAsItselfAtTheLatestVersion() {
        assertEquals(
                animate("0d000000"),
                encodedAt(
                        LATEST,
                        AnimateEntityPacket.newBuilder()
                                .setStopExpressionVersion(MolangVersion.LATEST)
                                .build()));
    }

    @Test
    void aNumberThatAnEarlyVersionGivesAMemberDecodesToThatMembersValue() {
        AnimateEntityPacket packet =
                assertInstanceOf(
                        AnimateEntityPacket.class,
                        EARLY.decodePacket(AnimateEntityPacket.ID, hex(animate("0d000000"))));
        assertEquals(14, packet.getStopExpressionVersionValue());
    }

    @Test
    void aNumberThatAnEarlyVersionCannotPlaceFailsToDecode() {
        assertEquals(
                "AnimateEntityPacket.stop_expression_version: unknown value at byte 7 of 13",
                assertThrows(
                                DecodeException.class,
                                () ->
                                        EARLY.decodePacket(
                                                AnimateEntityPacket.ID, hex(animate("0e000000"))))
                        .getMessage());
    }

    @Test
    void aNumberNoMemberHasAsItsValueDecodesToItselfAtAnEarlyVersion() {
        AnimateEntityPacket packet =
                assertInstanceOf(
                        AnimateEntityPacket.class,
                        EARLY.decodePacket(AnimateEntityPacket.ID, hex(animate("88130000"))));
        assertEquals(5000, packet.getStopExpressionVersionValue());
    }

    @Test
    void aNumberNoMemberHasAsItsValueEncodesAsItselfAtAnEarlyVersion() {
        assertEquals(
                animate("88130000"),
                encodedAt(
                        EARLY,
                        AnimateEntityPacket.newBuilder()
                                .setStopExpressionVersionValue(5000)
                                .build()));
    }

    @Test
    void theLatestCommandVersionEncodesAsItsNameAtAnEarlyVersion() {
        assertEquals(
                "0006706c617965720000000000000000000000000000000000000000000000000000066c6174657374",
                encodedAt(
                        EARLY,
                        CommandRequestPacket.newBuilder()
                                .setVersion(CurrentCmdVersion.LATEST)
                                .build()));
    }

    @Test
    void theNameLatestDecodesToTheMemberNumberedLikeItAtAnEarlyVersion() {
        CommandRequestPacket packet =
                assertInstanceOf(
                        CommandRequestPacket.class,
                        EARLY.decodePacket(
                                CommandRequestPacket.ID,
                                hex(
                                        "0006706c617965720000000000000000000000000000000000000000000000000000066c6174657374")));
        assertEquals(CurrentCmdVersion.LOCATE_STRUCTURE_OUTPUT, packet.getVersion());
    }

    @Test
    void theNameLatestEncodesAgainAfterItIsDecodedAtAnEarlyVersion() {
        assertEquals(
                "0006706c617965720000000000000000000000000000000000000000000000000000066c6174657374",
                encodedAt(
                        EARLY,
                        EARLY.decodePacket(
                                CommandRequestPacket.ID,
                                hex(
                                        "0006706c617965720000000000000000000000000000000000000000000000000000066c6174657374"))));
    }

    @Test
    void aCommandVersionAddedAfterAnEarlyVersionFailsToEncodeThere() {
        assertEquals(
                "CurrentCmdVersion: has no encoded name at protocol 729",
                assertThrows(
                                IllegalArgumentException.class,
                                () ->
                                        EARLY.encodePacket(
                                                CommandRequestPacket.newBuilder()
                                                        .setVersion(
                                                                CurrentCmdVersion
                                                                        .PLAY_SOUND_OUTPUT_FIX)
                                                        .build(),
                                                Unpooled.buffer()))
                        .getMessage());
    }

    @Test
    void theDefaultPersonaPieceFailsToEncodeWhereItsTypeHasNoName() {
        assertEquals(
                "PieceType: has no encoded name at protocol 729",
                assertThrows(
                                IllegalArgumentException.class,
                                () ->
                                        SerializedPersonaPieceHandle.codec(729)
                                                .encode(
                                                        SerializedPersonaPieceHandle
                                                                .getDefaultInstance(),
                                                        Unpooled.buffer()))
                        .getMessage());
    }

    @Test
    void theDefaultPersonaPieceEncodesWhereItsTypeIsANumber() {
        ByteBuf buf = Unpooled.buffer();
        SerializedPersonaPieceHandle.codec(2225)
                .encode(SerializedPersonaPieceHandle.getDefaultInstance(), buf);
        assertEquals("0000000000000000000000000000000000000000000000", ByteBufUtil.hexDump(buf));
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
