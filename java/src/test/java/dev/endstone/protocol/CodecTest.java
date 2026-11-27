package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import dev.endstone.protocol.internal.SerializationMode;
import dev.endstone.protocol.v2168.PlaySoundPacket_v2168;
import dev.endstone.protocol.v649.ClientboundDebugRendererPacket_v649;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import java.util.Collections;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

final class CodecTest {
  static Stream<Arguments> unsupported() {
    return Stream.of(argumentSet("below the oldest", 648), argumentSet("above the newest", 2260));
  }

  @Test
  void anEarlyCodecEncodesTheHudValuesAsOneByteEach() {
    ByteBuf buf = Unpooled.buffer();
    SetHudPacket.codec(729)
        .encode(SetHudPacket.newBuilder().addHudElementValue(2).setHudVisibleValue(1).build(), buf);
    assertEquals("010201", ByteBufUtil.hexDump(buf));
  }

  @Test
  void aLaterCodecEncodesTheHudValuesAsSignedVarInts() {
    ByteBuf buf = Unpooled.buffer();
    SetHudPacket.codec(786)
        .encode(SetHudPacket.newBuilder().addHudElementValue(2).setHudVisibleValue(1).build(), buf);
    assertEquals("010402", ByteBufUtil.hexDump(buf));
  }

  @Test
  void anEarlyCodecDecodesTheHudValues() {
    assertEquals(
        SetHudPacket.newBuilder().addHudElementValue(2).setHudVisibleValue(1).build(),
        SetHudPacket.codec(729)
            .decode(Unpooled.wrappedBuffer(ByteBufUtil.decodeHexDump("010201"))));
  }

  @Test
  void aTypeAbsentAtAProtocolHasNoCodec() {
    assertEquals(
        "v2168.PlaySoundPacket_v2168: is not a type at protocol 2225",
        assertThrows(IllegalArgumentException.class, () -> PlaySoundPacket_v2168.codec(2225))
            .getMessage());
  }

  @Test
  void aNumberNoReleaseReportsUsesTheCodecOfTheSnapshotBelowIt() {
    assertSame(ContainerClosePacket.codec(2193), ContainerClosePacket.codec(2200));
  }

  @ParameterizedTest
  @MethodSource("unsupported")
  void aNumberOutsideTheSupportedRangeHasNoCodec(int protocol) {
    assertEquals(
        "SetHudPacket: is not a type at protocol " + protocol,
        assertThrows(IllegalArgumentException.class, () -> SetHudPacket.codec(protocol))
            .getMessage());
  }

  @Test
  void aMixedTypeHasNoDefaultMode() {
    assertEquals(
        "SubChunkPos: no default mode at protocol 1001; it has CEREAL and MANUAL",
        assertThrows(IllegalArgumentException.class, () -> SubChunkPos.codec(1001)).getMessage());
  }

  @Test
  void aManualCodecWritesTheSubChunkPosAsVarInts() {
    ByteBuf buf = Unpooled.buffer();
    SubChunkPos.codec(1001, SerializationMode.MANUAL)
        .encode(SubChunkPos.newBuilder().setX(1).setY(-2).setZ(300).build(), buf);
    assertEquals("0203d804", ByteBufUtil.hexDump(buf));
  }

  @Test
  void aManualCodecReadsTheSubChunkPosFromVarInts() {
    assertEquals(
        SubChunkPos.newBuilder().setX(1).setY(-2).setZ(300).build(),
        SubChunkPos.codec(1001, SerializationMode.MANUAL)
            .decode(Unpooled.wrappedBuffer(ByteBufUtil.decodeHexDump("0203d804"))));
  }

  @Test
  void aCerealCodecWritesTheSubChunkPosAsFixedWidthInts() {
    ByteBuf buf = Unpooled.buffer();
    SubChunkPos.codec(1001, SerializationMode.CEREAL)
        .encode(SubChunkPos.newBuilder().setX(1).setY(-2).setZ(300).build(), buf);
    assertEquals("01000000feffffff2c010000", ByteBufUtil.hexDump(buf));
  }

  @Test
  void aModeAbsentAtAProtocolIsRejected() {
    assertEquals(
        "SubChunkPos: no manual mode at protocol 2168; it has DEFAULT",
        assertThrows(
                IllegalArgumentException.class,
                () -> SubChunkPos.codec(2168, SerializationMode.MANUAL))
            .getMessage());
  }

  @Test
  void aTypeAbsentAtAProtocolIsRejectedWhateverTheMode() {
    assertEquals(
        "ClientboundDataStorePacket: is not a type at protocol 729",
        assertThrows(
                IllegalArgumentException.class,
                () -> ClientboundDataStorePacket.codec(729, SerializationMode.CEREAL))
            .getMessage());
  }

  @Test
  void aCostItsOneByteEncodingCannotHoldFailsToEncode() {
    assertEquals(
        "ItemEnchantOption.cost: 300 is out of range",
        assertThrows(
                IllegalArgumentException.class,
                () ->
                    ItemEnchantOption.codec(2225)
                        .encode(
                            ItemEnchantOption.newBuilder().setCost(300).build(), Unpooled.buffer()))
            .getMessage());
  }

  @Test
  void aCostAtTheEdgeOfItsOneByteEncodingEncodesToItsByte() {
    ByteBuf buf = Unpooled.buffer();
    ItemEnchantOption.codec(2225).encode(ItemEnchantOption.newBuilder().setCost(255).build(), buf);
    assertEquals("ff000000000000000000", ByteBufUtil.hexDump(buf));
  }

  @Test
  void pre898DebugRendererMarkerEncodesColorAsFourFloats() {
    ClientboundDebugRendererPacket_v649 packet =
        ClientboundDebugRendererPacket_v649.newBuilder()
            .setType(ClientboundDebugRendererPacket_v649.Type.ADD_DEBUG_MARKER_CUBE)
            .setDebugMarkerData(
                ClientboundDebugRendererPacket.DebugMarkerData.newBuilder()
                    .setText("marker")
                    .setPosition(Vec3.newBuilder().setX(1.0f).setY(2.0f).setZ(3.0f).build())
                    .setColor(
                        Color.newBuilder().setR(1.0f).setG(0.5f).setB(0.25f).setA(0.75f).build())
                    .setDurationMs(1500L)
                    .build())
            .build();
    String expected =
        "02000000066d61726b65720000803f00000040000040400000803f0000003f0000803e0000403fdc05000000000000";
    ByteBuf buf = Unpooled.buffer();
    ClientboundDebugRendererPacket_v649.codec(859).encode(packet, buf);
    assertEquals(expected, ByteBufUtil.hexDump(buf));
    assertEquals(
        packet,
        ClientboundDebugRendererPacket_v649.codec(859)
            .decode(Unpooled.wrappedBuffer(ByteBufUtil.decodeHexDump(expected))));
  }

  static Stream<Arguments> pre898AvailableCommandsBoundaries() {
    return Stream.of(
        argumentSet("small table uses uint8", 1, 0, 13, "0165010000000000"),
        argumentSet("256 values uses uint8", 256, 255, 269, "016501ff00000000"),
        argumentSet("257 values uses uint16", 257, 256, 271, "016501000100000000"),
        argumentSet("65536 values uses uint16", 65536, 65535, 65551, "016501ffff00000000"),
        argumentSet("65537 values uses uint32", 65537, 65536, 65554, "0165010000010000000000"));
  }

  @ParameterizedTest
  @MethodSource("pre898AvailableCommandsBoundaries")
  void pre898AvailableCommandsEncodesEnumIndicesByEnumValueCount(
      int valueCount, int index, int expectedBytes, String expectedTailHex) {
    AvailableCommandsPacket packet =
        AvailableCommandsPacket.newBuilder()
            .addAllEnumValues(Collections.nCopies(valueCount, ""))
            .addEnums(
                AvailableCommandsPacket.EnumData.newBuilder().setName("e").addValues(index).build())
            .build();
    ByteBuf buf = Unpooled.buffer();
    AvailableCommandsPacket.codec(859).encode(packet, buf);
    assertEquals(expectedBytes, buf.readableBytes());
    String hex = ByteBufUtil.hexDump(buf);
    assertEquals(expectedTailHex, hex.substring(hex.length() - expectedTailHex.length()));
    assertEquals(packet, AvailableCommandsPacket.codec(859).decode(buf));
    assertEquals(0, buf.readableBytes());
  }

  @Test
  void pre898AvailableCommandsRejectsEnumIndexOutsideChosenWidth() {
    AvailableCommandsPacket packet =
        AvailableCommandsPacket.newBuilder()
            .addEnumValues("a")
            .addEnums(
                AvailableCommandsPacket.EnumData.newBuilder().setName("e").addValues(256).build())
            .build();
    assertThrows(
        IllegalArgumentException.class,
        () -> AvailableCommandsPacket.codec(859).encode(packet, Unpooled.buffer()));
  }

  @Test
  void v898AvailableCommandsKeepsFixedUint32EnumIndices() {
    AvailableCommandsPacket packet =
        AvailableCommandsPacket.newBuilder()
            .addEnumValues("")
            .addEnums(
                AvailableCommandsPacket.EnumData.newBuilder().setName("e").addValues(0).build())
            .build();
    String expected = "01000000010165010000000000000000";
    ByteBuf buf = Unpooled.buffer();
    AvailableCommandsPacket.codec(898).encode(packet, buf);
    assertEquals(expected, ByteBufUtil.hexDump(buf));
    assertEquals(
        packet,
        AvailableCommandsPacket.codec(898)
            .decode(Unpooled.wrappedBuffer(ByteBufUtil.decodeHexDump(expected))));
  }
}
