package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import org.junit.jupiter.api.Test;

final class CodecTest {
    @Test
    void anEarlyCodecEncodesTheHudValuesAsOneByteEach() {
        ByteBuf buf = Unpooled.buffer();
        SetHudPacket.codec(729)
                .encode(
                        SetHudPacket.newBuilder()
                                .addHudElementValue(2)
                                .setHudVisibleValue(1)
                                .build(),
                        buf);
        assertEquals("010201", ByteBufUtil.hexDump(buf));
    }

    @Test
    void aLaterCodecEncodesTheHudValuesAsSignedVarInts() {
        ByteBuf buf = Unpooled.buffer();
        SetHudPacket.codec(786)
                .encode(
                        SetHudPacket.newBuilder()
                                .addHudElementValue(2)
                                .setHudVisibleValue(1)
                                .build(),
                        buf);
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
                "v2168.PlaySoundPacket: is not a type at protocol 2225",
                assertThrows(
                                IllegalArgumentException.class,
                                () -> dev.endstone.protocol.v2168.PlaySoundPacket.codec(2225))
                        .getMessage());
    }

    @Test
    void aMixedTypeHasNoDefaultMode() {
        assertEquals(
                "SubChunkPos: no default mode at protocol 1001; it has CEREAL and MANUAL",
                assertThrows(IllegalArgumentException.class, () -> SubChunkPos.codec(1001))
                        .getMessage());
    }

    @Test
    void aManualCodecWritesTheSubChunkPosAsVarInts() {
        ByteBuf buf = Unpooled.buffer();
        SubChunkPos.codec(1001, SerializationMode.MANUAL)
                .encode(SubChunkPos.newBuilder().setX(1).setY(-2).setZ(300).build(), buf);
        assertEquals("0203d804", ByteBufUtil.hexDump(buf));
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
    void aTypeAbsentAtAProtocolIsRejectedBeforeItsMode() {
        assertEquals(
                "v2168.PlaySoundPacket: is not a type at protocol 2225",
                assertThrows(
                                IllegalArgumentException.class,
                                () ->
                                        dev.endstone.protocol.v2168.PlaySoundPacket.codec(
                                                2225, SerializationMode.CEREAL))
                        .getMessage());
    }
}
