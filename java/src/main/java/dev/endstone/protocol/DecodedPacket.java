package dev.endstone.protocol;

import java.util.Objects;
import org.jetbrains.annotations.NotNull;

/** A packet with the header it was framed by. */
public record DecodedPacket(@NotNull PacketHeader header, @NotNull Packet packet) {
    public DecodedPacket {
        Objects.requireNonNull(header);
        Objects.requireNonNull(packet);
    }
}
