package dev.endstone.protocol;

/** A packet body with its id. */
public interface Packet extends Message {
  int getPacketId();
}
