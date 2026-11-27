package dev.endstone.protocol;

import io.netty.buffer.ByteBuf;
import java.util.ArrayList;
import java.util.List;
import org.jetbrains.annotations.NotNull;

final class AvailableCommandsPacketEnumDataCodec622 {

  private AvailableCommandsPacketEnumDataCodec622() {}

  static void encode(
      @NotNull AvailableCommandsPacket.EnumData value, @NotNull ByteBuf buf, long argument) {
    ByteBufCodec.writeString(buf, value.getName());
    ByteBufCodec.writeUnsignedVarInt(buf, value.getValuesCount());
    for (int index : value.getValuesList()) {
      if (argument <= 0x100) {
        buf.writeByte(narrowed(index, 0xFF));
      } else if (argument <= 0x10000) {
        buf.writeShortLE(narrowed(index, 0xFFFF));
      } else {
        buf.writeIntLE(index);
      }
    }
  }

  static @NotNull AvailableCommandsPacket.EnumData decode(@NotNull ByteBuf buf, long argument) {
    AvailableCommandsPacket.EnumData.Builder out = AvailableCommandsPacket.EnumData.newBuilder();
    try {
      out.setName(ByteBufCodec.readString(buf));
    } catch (DecodeException e) {
      throw e.prepend("name").setUnfinishedMessage(out.build());
    }
    try {
      int count = ByteBufCodec.toCount(buf, ByteBufCodec.readUvarint32Count(buf));
      List<Integer> values = new ArrayList<>(ByteBufCodec.initialCapacity(count));
      for (int i = 0; i < count; i++) {
        try {
          values.add(
              argument <= 0x100
                  ? ByteBufCodec.readUnsignedByte(buf)
                  : argument <= 0x10000
                      ? ByteBufCodec.readUnsignedShortLE(buf)
                      : ByteBufCodec.readIntLE(buf));
        } catch (DecodeException e) {
          throw e.prepend(i);
        }
      }
      out.addAllValues(values);
    } catch (DecodeException e) {
      throw e.prepend("values").setUnfinishedMessage(out.build());
    }
    return out.build();
  }

  private static int narrowed(int index, int mask) {
    if ((index & mask) != index) {
      throw new IllegalArgumentException(
          "EnumData.values: " + Integer.toUnsignedString(index) + " is out of range");
    }
    return index;
  }
}
