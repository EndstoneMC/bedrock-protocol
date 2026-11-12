package dev.endstone.protocol;

/** A packet with the header it arrived under. */
public record DecodedPacket(PacketHeader header, Packet packet) {}
