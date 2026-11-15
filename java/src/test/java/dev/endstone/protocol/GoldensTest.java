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
            int version = Integer.parseInt(folder.substring(1));
            int packetId = Integer.parseInt(stem.substring(0, stem.indexOf('_')));
            try (Reader reader = Files.newBufferedReader(file)) {
                for (JsonElement entry : JsonParser.parseReader(reader).getAsJsonArray()) {
                    String id = entry.getAsJsonObject().get("id").getAsString();
                    String bytes = entry.getAsJsonObject().get("bytes").getAsString();
                    String value = entry.getAsJsonObject().get("value").toString();
                    cases.add(
                            argumentSet(
                                    folder + "/" + stem + "/" + id,
                                    version,
                                    packetId,
                                    bytes,
                                    value));
                }
            }
        }
        return cases.build();
    }

    private static Packet decode(int version, int packetId, String bytes) {
        return ProtocolVersion.of(version)
                .orElseThrow()
                .decodePacket(packetId, Unpooled.wrappedBuffer(ByteBufUtil.decodeHexDump(bytes)));
    }

    private static String encoded(int version, Packet packet) {
        ByteBuf buf = Unpooled.buffer();
        ProtocolVersion.of(version).orElseThrow().encodePacket(packet, buf);
        return ByteBufUtil.hexDump(buf);
    }

    @ParameterizedTest
    @MethodSource("cases")
    void reEncodingADecodedGoldenGivesItsBytes(int version, int packetId, String bytes) {
        assertEquals(bytes, encoded(version, decode(version, packetId, bytes)));
    }

    @ParameterizedTest
    @MethodSource("cases")
    void aDecodedGoldenHasItsFilesPacketId(int version, int packetId, String bytes) {
        assertEquals(packetId, decode(version, packetId, bytes).getPacketId());
    }

    @ParameterizedTest
    @MethodSource("cases")
    void decodingTheReEncodedBytesGivesAnEqualPacket(int version, int packetId, String bytes) {
        Packet packet = decode(version, packetId, bytes);
        assertEquals(packet, decode(version, packetId, encoded(version, packet)));
    }

    @ParameterizedTest
    @MethodSource("cases")
    void encodingTheLoadedPacketGivesTheBytes(int version, int packetId, String bytes, String value)
            throws ReflectiveOperationException {
        Packet decoded = decode(version, packetId, bytes);
        Packet loaded = CaseLoader.load(version, decoded.getClass(), JsonParser.parseString(value));
        assertEquals(bytes, encoded(version, loaded));
    }

    @ParameterizedTest
    @MethodSource("cases")
    void decodingTheBytesGivesTheLoadedPacket(int version, int packetId, String bytes, String value)
            throws ReflectiveOperationException {
        Packet decoded = decode(version, packetId, bytes);
        Packet loaded = CaseLoader.load(version, decoded.getClass(), JsonParser.parseString(value));
        assertEquals(loaded, decoded);
    }
}
