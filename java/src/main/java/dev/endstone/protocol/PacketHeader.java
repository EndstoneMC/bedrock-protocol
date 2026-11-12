package dev.endstone.protocol;

import io.netty.buffer.ByteBuf;

/** The id and sub ids that open a packet. */
public record PacketHeader(int packetId, int recipientSubId, int senderSubId) {
    public PacketHeader {
        if ((packetId & ~0x3FF) != 0) {
            throw new IllegalArgumentException("PacketHeader.packetId: cannot hold " + packetId);
        }
        if ((recipientSubId & ~3) != 0) {
            throw new IllegalArgumentException(
                    "PacketHeader.recipientSubId: cannot hold " + recipientSubId);
        }
        if ((senderSubId & ~3) != 0) {
            throw new IllegalArgumentException(
                    "PacketHeader.senderSubId: cannot hold " + senderSubId);
        }
    }

    public static PacketHeader decode(ByteBuf buf) {
        return Wire.decode(buf, DecodeLimits.DEFAULT, "PacketHeader", PacketHeader::read);
    }

    public static PacketHeader read(ByteBuf buf, DecodeBudget budget) {
        int bits = Wire.readUvarint32(buf);
        return new PacketHeader(bits & 0x3FF, (bits >>> 10) & 3, (bits >>> 12) & 3);
    }

    public void encode(ByteBuf buf) {
        Wire.writeUvarint32(buf, packetId | recipientSubId << 10 | senderSubId << 12);
    }
}
