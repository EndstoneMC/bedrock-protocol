package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import dev.endstone.protocol.internal.SerializationMode;
import dev.endstone.protocol.v2168.PlaySoundPacket_v2168;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

final class CodecTest {
  static Stream<Arguments> unsupported() {
    return Stream.of(argumentSet("below the oldest", 661), argumentSet("above the newest", 2260));
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
}
