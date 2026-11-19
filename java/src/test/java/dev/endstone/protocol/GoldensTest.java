package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import java.io.IOException;
import java.io.Reader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

final class GoldensTest {
    static Stream<Arguments> cases() throws IOException {
        Path root = Paths.get(System.getProperty("goldens.dir"));
        List<Path> files;
        try (Stream<Path> walk = Files.walk(root)) {
            files =
                    walk.filter(path -> path.getFileName().toString().matches("\\d+_.*\\.json"))
                            .sorted()
                            .toList();
        }
        Stream.Builder<Arguments> cases = Stream.builder();
        for (Path file : files) {
            String folder = file.getParent().getFileName().toString();
            String name = file.getFileName().toString();
            String stem = name.substring(0, name.length() - ".json".length());
            Protocol protocol = Protocol.of(Integer.parseInt(folder.substring(1))).orElseThrow();
            int packetId = Integer.parseInt(stem.substring(0, stem.indexOf('_')));
            try (Reader reader = Files.newBufferedReader(file)) {
                for (JsonElement entry : JsonParser.parseReader(reader).getAsJsonArray()) {
                    String id = entry.getAsJsonObject().get("id").getAsString();
                    String bytes = entry.getAsJsonObject().get("bytes").getAsString();
                    String value = entry.getAsJsonObject().get("value").toString();
                    cases.add(
                            argumentSet(
                                    folder + "/" + stem + "/" + id,
                                    protocol,
                                    packetId,
                                    bytes,
                                    value));
                }
            }
        }
        return cases.build();
    }

    private static byte[] hex(String hex) {
        return ByteBufUtil.decodeHexDump(hex);
    }

    private static byte[] framed(int packetId, String bytes) {
        ByteBuf buf = Unpooled.buffer();
        new PacketHeader(packetId, 0, 0).encode(buf);
        buf.writeBytes(hex(bytes));
        return ByteBufUtil.getBytes(buf);
    }

    private static Class<? extends Packet> type(Protocol protocol, int packetId, String bytes) {
        return protocol.decodePacket(framed(packetId, bytes)).packet().getClass();
    }

    @ParameterizedTest
    @MethodSource("cases")
    void reEncodingADecodedGoldenGivesItsBytes(Protocol protocol, int packetId, String bytes) {
        Class<? extends Packet> type = type(protocol, packetId, bytes);
        Packet decoded = protocol.decode(type, hex(bytes));
        assertEquals(bytes, ByteBufUtil.hexDump(protocol.encode(decoded)));
    }

    @ParameterizedTest
    @MethodSource("cases")
    void aFramedGoldenDecodesToItsFilesPacketId(Protocol protocol, int packetId, String bytes) {
        assertEquals(
                packetId, protocol.decodePacket(framed(packetId, bytes)).packet().getPacketId());
    }

    @ParameterizedTest
    @MethodSource("cases")
    void aFramedGoldenDecodesToTheDecodedBody(Protocol protocol, int packetId, String bytes) {
        Class<? extends Packet> type = type(protocol, packetId, bytes);
        assertEquals(
                protocol.decode(type, hex(bytes)),
                protocol.decodePacket(framed(packetId, bytes)).packet());
    }

    @ParameterizedTest
    @MethodSource("cases")
    void decodingTheReEncodedBytesGivesAnEqualPacket(
            Protocol protocol, int packetId, String bytes) {
        Class<? extends Packet> type = type(protocol, packetId, bytes);
        Packet packet = protocol.decode(type, hex(bytes));
        assertEquals(packet, protocol.decode(type, protocol.encode(packet)));
    }

    @ParameterizedTest
    @MethodSource("cases")
    void encodingTheLoadedPacketGivesTheBytes(
            Protocol protocol, int packetId, String bytes, String value)
            throws ReflectiveOperationException {
        Packet loaded =
                CaseLoader.load(
                        protocol.version(),
                        type(protocol, packetId, bytes),
                        JsonParser.parseString(value));
        assertEquals(bytes, ByteBufUtil.hexDump(protocol.encode(loaded)));
    }

    @ParameterizedTest
    @MethodSource("cases")
    void decodingTheBytesGivesTheLoadedPacket(
            Protocol protocol, int packetId, String bytes, String value)
            throws ReflectiveOperationException {
        Class<? extends Packet> type = type(protocol, packetId, bytes);
        Packet loaded = CaseLoader.load(protocol.version(), type, JsonParser.parseString(value));
        assertEquals(loaded, protocol.decode(type, hex(bytes)));
    }
}
