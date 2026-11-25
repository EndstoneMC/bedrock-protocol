package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;

import dev.endstone.protocol.nbt.CompoundTag;
import dev.endstone.protocol.v686.PlayerSkinPacket_v686;
import dev.endstone.protocol.v686.SerializedPersonaPieceHandle_v686;
import dev.endstone.protocol.v686.SerializedSkinRef_v686;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import org.junit.jupiter.api.Test;

final class MessageTest {
  private static String animate(String version) {
    return "000000" + version + "00" + "00000000" + "00";
  }

  private static byte[] hex(String hex) {
    return ByteBufUtil.decodeHexDump(hex);
  }

  private static String encoded(Packet value) {
    return ByteBufUtil.hexDump(Protocol.encode(value));
  }

  private static <T extends Packet> DecodeException failure(Class<T> type, String hex) {
    return assertThrows(DecodeException.class, () -> Protocol.decode(type, hex(hex)));
  }

  @Test
  void truncatedInputNamesTheFieldThatFailed() {
    assertEquals(
        "ToastRequestPacket.content: truncated at byte 3 of 3",
        failure(ToastRequestPacket.class, "026162").getMessage());
  }

  @Test
  void truncatedInputKeepsTheFieldsBeforeTheCut() {
    ToastRequestPacket unfinished =
        assertInstanceOf(
            ToastRequestPacket.class,
            failure(ToastRequestPacket.class, "026162").getUnfinishedMessage());
    assertEquals("ab", unfinished.getTitle());
  }

  @Test
  void truncatedInputLeavesTheFieldsAfterTheCutAtTheirDefaults() {
    ToastRequestPacket unfinished =
        assertInstanceOf(
            ToastRequestPacket.class,
            failure(ToastRequestPacket.class, "026162").getUnfinishedMessage());
    assertEquals("", unfinished.getContent());
  }

  @Test
  void aNarrowSetterRejectsAValueItCannotHold() {
    ActorPickRequestPacket.Builder builder = ActorPickRequestPacket.newBuilder();
    assertEquals(
        "ActorPickRequestPacket.maxSlots: cannot hold 256",
        assertThrows(IllegalArgumentException.class, () -> builder.setMaxSlots(256)).getMessage());
  }

  @Test
  void anUnknownUnionIndexIsAnUnknownValue() {
    assertEquals(
        "TextPacket.body: unknown value at byte 2 of 2",
        failure(TextPacket.class, "0009").getMessage());
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
    PlayStatusPacket packet = Protocol.decode(PlayStatusPacket.class, hex("000003e7"));
    assertEquals(PlayStatus.UNRECOGNIZED, packet.getStatus());
  }

  @Test
  void anUnknownEnumNumberKeepsItsNumber() {
    PlayStatusPacket packet = Protocol.decode(PlayStatusPacket.class, hex("000003e7"));
    assertEquals(999, packet.getStatusValue());
  }

  @Test
  void anUnknownEnumNumberReEncodesAsItself() {
    assertEquals("000003e7", encoded(Protocol.decode(PlayStatusPacket.class, hex("000003e7"))));
  }

  @Test
  void aPacketIdAddedAfterAVersionFailsToDecodeAtThatVersion() {
    assertEquals(
        "PacketViolationWarningPacket.violating_packet_id: unknown value at byte 4 of 5",
        assertThrows(
                DecodeException.class,
                () -> Protocol.v729.decode(PacketViolationWarningPacket.class, hex("0000940500")))
            .getMessage());
  }

  @Test
  void aPacketIdAddedAfterAVersionFailsToEncodeAtThatVersion() {
    assertEquals(
        "MinecraftPacketIds: 330 has no number at protocol 729",
        assertThrows(
                IllegalArgumentException.class,
                () ->
                    Protocol.v729.encode(
                        PacketViolationWarningPacket.newBuilder()
                            .setViolatingPacketId(MinecraftPacketIds.CLIENTBOUND_DATA_STORE)
                            .build()))
            .getMessage());
  }

  @Test
  void theLatestMolangVersionEncodesAsTheNumberItHasAtAnEarlyVersion() {
    assertEquals(
        animate("0c000000"),
        ByteBufUtil.hexDump(
            Protocol.v729.encode(
                AnimateEntityPacket.newBuilder()
                    .setStopExpressionVersion(MolangVersion.LATEST)
                    .build())));
  }

  @Test
  void theLatestMolangVersionEncodesAsItselfAtTheLatestVersion() {
    assertEquals(
        animate("0d000000"),
        encoded(
            AnimateEntityPacket.newBuilder()
                .setStopExpressionVersion(MolangVersion.LATEST)
                .build()));
  }

  @Test
  void aNumberThatAnEarlyVersionGivesAMemberDecodesToThatMembersValue() {
    AnimateEntityPacket packet =
        Protocol.v729.decode(AnimateEntityPacket.class, hex(animate("0d000000")));
    assertEquals(14, packet.getStopExpressionVersionValue());
  }

  @Test
  void aNumberThatAnEarlyVersionCannotPlaceFailsToDecode() {
    assertEquals(
        "AnimateEntityPacket.stop_expression_version: unknown value at byte 7 of 13",
        assertThrows(
                DecodeException.class,
                () -> Protocol.v729.decode(AnimateEntityPacket.class, hex(animate("0e000000"))))
            .getMessage());
  }

  @Test
  void aNumberNoMemberHasAsItsValueDecodesToItselfAtAnEarlyVersion() {
    AnimateEntityPacket packet =
        Protocol.v729.decode(AnimateEntityPacket.class, hex(animate("88130000")));
    assertEquals(5000, packet.getStopExpressionVersionValue());
  }

  @Test
  void aNumberNoMemberHasAsItsValueEncodesAsItselfAtAnEarlyVersion() {
    assertEquals(
        animate("88130000"),
        ByteBufUtil.hexDump(
            Protocol.v729.encode(
                AnimateEntityPacket.newBuilder().setStopExpressionVersionValue(5000).build())));
  }

  @Test
  void theLatestCommandVersionEncodesAsItsNameAtAnEarlyVersion() {
    assertEquals(
        "0006706c617965720000000000000000000000000000000000000000000000000000066c6174657374",
        ByteBufUtil.hexDump(
            Protocol.v898.encode(
                CommandRequestPacket.newBuilder().setVersion(CurrentCmdVersion.LATEST).build())));
  }

  @Test
  void theNameLatestDecodesToLatestAtAnEarlyVersion() {
    CommandRequestPacket packet =
        Protocol.v898.decode(
            CommandRequestPacket.class,
            hex(
                "0006706c617965720000000000000000000000000000000000000000000000000000066c6174657374"));
    assertEquals(CurrentCmdVersion.LATEST, packet.getVersion());
  }

  @Test
  void theNameLatestDecodedAtOneProtocolEncodesAsLatestAtAnOlderOne() {
    String latest =
        "072f736179206869106175746f6d6174696f6e706c61796572efcdab8967452301"
            + "1032547698badcfe057265712d31feffffffffffffff01066c6174657374";
    assertEquals(
        latest,
        ByteBufUtil.hexDump(
            Protocol.v2168.encode(Protocol.v2193.decode(CommandRequestPacket.class, hex(latest)))));
  }

  @Test
  void theNameLatestEncodesAgainAfterItIsDecodedAtAnEarlyVersion() {
    assertEquals(
        "0006706c617965720000000000000000000000000000000000000000000000000000066c6174657374",
        ByteBufUtil.hexDump(
            Protocol.v898.encode(
                Protocol.v898.decode(
                    CommandRequestPacket.class,
                    hex(
                        "0006706c617965720000000000000000000000000000000000000000000000000000066c6174657374")))));
  }

  @Test
  void aCommandVersionAddedAfterAnEarlyVersionFailsToEncodeThere() {
    assertEquals(
        "CurrentCmdVersion: has no encoded name at protocol 898",
        assertThrows(
                IllegalArgumentException.class,
                () ->
                    Protocol.v898.encode(
                        CommandRequestPacket.newBuilder()
                            .setVersion(CurrentCmdVersion.PLAY_SOUND_OUTPUT_FIX)
                            .build()))
            .getMessage());
  }

  @Test
  void theDefaultPersonaPieceEncodesWhereItsTypeIsAName() {
    assertEquals(
        "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
            + "000004736c696d0001000000000f706572736f6e615f756e6b6e6f776e000000000000000000000000000000",
        ByteBufUtil.hexDump(
            Protocol.v712.encode(
                PlayerSkinPacket_v686.newBuilder()
                    .setSkin(
                        SerializedSkinRef_v686.newBuilder()
                            .addPersonaPieces(
                                SerializedPersonaPieceHandle_v686.getDefaultInstance())
                            .build())
                    .build())));
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
        Protocol.decode(AvailableActorIdentifiersPacket.class, hex("0a0000"));
    CompoundTag copy = packet.getIdentifierList();
    copy.putInt("x", 1);
    assertFalse(packet.getIdentifierList().contains("x"));
  }
}
