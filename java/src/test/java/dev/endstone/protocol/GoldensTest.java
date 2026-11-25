package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import io.netty.buffer.ByteBufUtil;
import java.io.IOException;
import java.io.Reader;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.net.URISyntaxException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

final class GoldensTest {
  private record Pinned(int version, Method encoder, Method decoder) {
    byte[] encode(Packet packet) throws ReflectiveOperationException {
      return (byte[]) encoder.invoke(null, packet);
    }

    Packet decode(Class<? extends Packet> type, byte[] bytes) throws ReflectiveOperationException {
      return (Packet) decoder.invoke(null, type, bytes);
    }
  }

  static Stream<Arguments> cases()
      throws IOException, URISyntaxException, ReflectiveOperationException {
    Path classes =
        Path.of(Packet.class.getProtectionDomain().getCodeSource().getLocation().toURI());
    List<Path> classFiles;
    try (Stream<Path> walk = Files.walk(classes)) {
      classFiles =
          walk.filter(
                  path ->
                      path.getFileName().toString().endsWith(".class")
                          && !path.getFileName().toString().contains("$"))
              .toList();
    }
    Map<Integer, List<Class<? extends Packet>>> packets = new HashMap<>();
    for (Path classFile : classFiles) {
      String name = classes.relativize(classFile).toString();
      name =
          name.substring(0, name.length() - ".class".length())
              .replace(classFile.getFileSystem().getSeparator(), ".");
      Class<?> type = Class.forName(name, false, Packet.class.getClassLoader());
      if (Packet.class.isAssignableFrom(type)
          && !type.isInterface()
          && !Modifier.isAbstract(type.getModifiers())) {
        Packet packet = (Packet) type.getMethod("getDefaultInstance").invoke(null);
        packets
            .computeIfAbsent(packet.getPacketId(), key -> new ArrayList<>())
            .add(type.asSubclass(Packet.class));
      }
    }

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
      Class<?> pinnedClass = Class.forName(Protocol.class.getName() + "$" + folder);
      Pinned protocol =
          new Pinned(
              pinnedClass.getField("VERSION").getInt(null),
              pinnedClass.getMethod("encode", Packet.class),
              pinnedClass.getMethod("decode", Class.class, byte[].class));
      int packetId = Integer.parseInt(stem.substring(0, stem.indexOf('_')));
      List<Class<? extends Packet>> accepted = new ArrayList<>();
      for (Class<? extends Packet> candidate : packets.getOrDefault(packetId, List.of())) {
        try {
          candidate.getMethod("codec", int.class).invoke(null, protocol.version());
          accepted.add(candidate);
        } catch (InvocationTargetException e) {
          if (!(e.getCause() instanceof IllegalArgumentException)) {
            throw e;
          }
        }
      }
      if (accepted.size() != 1) {
        throw new IllegalStateException(
            file
                + ": "
                + accepted.size()
                + " packets with id "
                + packetId
                + " accept protocol "
                + folder);
      }
      try (Reader reader = Files.newBufferedReader(file)) {
        for (JsonElement entry : JsonParser.parseReader(reader).getAsJsonArray()) {
          String id = entry.getAsJsonObject().get("id").getAsString();
          String bytes = entry.getAsJsonObject().get("bytes").getAsString();
          String value = entry.getAsJsonObject().get("value").toString();
          cases.add(
              argumentSet(
                  folder + "/" + stem + "/" + id, protocol, accepted.getFirst(), bytes, value));
        }
      }
    }
    return cases.build();
  }

  private static byte[] hex(String hex) {
    return ByteBufUtil.decodeHexDump(hex);
  }

  @ParameterizedTest
  @MethodSource("cases")
  void reEncodingADecodedGoldenGivesItsBytes(
      Pinned protocol, Class<? extends Packet> type, String bytes)
      throws ReflectiveOperationException {
    Packet decoded = protocol.decode(type, hex(bytes));
    assertEquals(bytes, ByteBufUtil.hexDump(protocol.encode(decoded)));
  }

  @ParameterizedTest
  @MethodSource("cases")
  void decodingTheReEncodedBytesGivesAnEqualPacket(
      Pinned protocol, Class<? extends Packet> type, String bytes)
      throws ReflectiveOperationException {
    Packet packet = protocol.decode(type, hex(bytes));
    assertEquals(packet, protocol.decode(type, protocol.encode(packet)));
  }

  @ParameterizedTest
  @MethodSource("cases")
  void encodingTheLoadedPacketGivesTheBytes(
      Pinned protocol, Class<? extends Packet> type, String bytes, String value)
      throws ReflectiveOperationException {
    Packet loaded = CaseLoader.load(protocol.version(), type, JsonParser.parseString(value));
    assertEquals(bytes, ByteBufUtil.hexDump(protocol.encode(loaded)));
  }

  @ParameterizedTest
  @MethodSource("cases")
  void decodingTheBytesGivesTheLoadedPacket(
      Pinned protocol, Class<? extends Packet> type, String bytes, String value)
      throws ReflectiveOperationException {
    Packet loaded = CaseLoader.load(protocol.version(), type, JsonParser.parseString(value));
    assertEquals(loaded, protocol.decode(type, hex(bytes)));
  }
}
