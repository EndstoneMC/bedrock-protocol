package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

final class ProtocolVersionTest {
  static Stream<Arguments> names() {
    return Stream.of(
        argumentSet("first release of 729", 729, "1.21.30"),
        argumentSet("860 has its own release", 860, "1.21.124"),
        argumentSet("2169 has its own release", 2169, "1.26.45"),
        argumentSet("first release of 2225", 2225, "1.26.60"));
  }

  static Stream<Arguments> unlisted() {
    return Stream.of(
        argumentSet("2170 after 2169's release", 2170, "1.26.45"),
        argumentSet("2200 after 2193's release", 2200, "1.26.50"));
  }

  static Stream<Arguments> unlistedProtocols() {
    return Stream.of(argumentSet("2170", 2170), argumentSet("2200", 2200));
  }

  static Stream<Arguments> unsupported() {
    return Stream.of(argumentSet("below the oldest", 617), argumentSet("above the newest", 2260));
  }

  @Test
  void supportedVersionsAscendByProtocol() {
    List<Integer> protocols =
        ProtocolVersion.SUPPORTED_VERSIONS.stream().map(ProtocolVersion::getProtocol).toList();
    assertEquals(protocols.stream().sorted().toList(), protocols);
  }

  @Test
  void theMinimumVersionIsTheFirstSupported() {
    assertSame(ProtocolVersion.SUPPORTED_VERSIONS.getFirst(), ProtocolVersion.MINIMUM_VERSION);
  }

  @Test
  void theMaximumVersionIsTheLastSupported() {
    assertSame(ProtocolVersion.SUPPORTED_VERSIONS.getLast(), ProtocolVersion.MAXIMUM_VERSION);
  }

  @ParameterizedTest
  @MethodSource("names")
  void aVersionIsNamedAfterTheFirstReleaseThatShippedIt(int protocol, String name) {
    assertEquals(name, ProtocolVersion.get(protocol).orElseThrow().getName());
  }

  @Test
  void aVersionKnowsItsProtocol() {
    assertEquals(2225, ProtocolVersion.get(2225).orElseThrow().getProtocol());
  }

  @Test
  void aListedNumberFindsTheSupportedVersionItself() {
    assertSame(ProtocolVersion.MAXIMUM_VERSION, ProtocolVersion.get(2259).orElseThrow());
  }

  @ParameterizedTest
  @MethodSource("unlisted")
  void aNumberNoReleaseReportsIsNamedForTheReleaseBelowIt(int protocol, String name) {
    assertEquals(name, ProtocolVersion.get(protocol).orElseThrow().getName());
  }

  @ParameterizedTest
  @MethodSource("unlistedProtocols")
  void aNumberNoReleaseReportsKeepsItsOwnProtocol(int protocol) {
    assertEquals(protocol, ProtocolVersion.get(protocol).orElseThrow().getProtocol());
  }

  @ParameterizedTest
  @MethodSource("unsupported")
  void aNumberOutsideTheSupportedRangeHasNoVersion(int protocol) {
    assertTrue(ProtocolVersion.get(protocol).isEmpty());
  }
}
