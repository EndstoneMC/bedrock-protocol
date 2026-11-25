package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import dev.endstone.protocol.internal.ActorTypeNumbering;
import dev.endstone.protocol.internal.MinecraftPacketIdsNumbering;
import dev.endstone.protocol.internal.MolangVersionNumbering;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

final class NumberingTest {
  @Test
  void theLatestMolangVersionHasTheNumberItsDeclaredAliasHasAtAnEarlyProtocol() {
    assertEquals(12, MolangVersionNumbering.toNumber(729, 13));
  }

  @Test
  void aMolangVersionIsItsOwnNumberAtTheLatestProtocol() {
    assertEquals(13, MolangVersionNumbering.toNumber(2225, 13));
  }

  @Test
  void aMolangVersionNumberAnEarlyProtocolGivesAMemberHasThatMembersValue() {
    assertEquals(14, MolangVersionNumbering.fromNumber(729, 13));
  }

  @Test
  void aMolangVersionNumberAnEarlyProtocolCannotPlaceDoesNotDecode() {
    assertFalse(MolangVersionNumbering.decodes(729, 14));
  }

  @Test
  void aMolangVersionNumberAnEarlyProtocolCannotPlaceFailsToConvert() {
    assertEquals(
        "MolangVersion: 14 has no value at protocol 729",
        assertThrows(
                IllegalArgumentException.class, () -> MolangVersionNumbering.fromNumber(729, 14))
            .getMessage());
  }

  @Test
  void aPacketIdAnEarlyProtocolLacksHasNoNumberThere() {
    assertEquals(
        "MinecraftPacketIds: 330 has no number at protocol 729",
        assertThrows(
                IllegalArgumentException.class,
                () -> MinecraftPacketIdsNumbering.toNumber(729, 330))
            .getMessage());
  }

  @Test
  void aPacketIdNumberNoEarlyProtocolPlacesDoesNotDecode() {
    assertFalse(MinecraftPacketIdsNumbering.decodes(729, 330));
  }

  static Stream<Arguments> placedActorTypeNumbers() {
    return Stream.of(
        argumentSet("number 0", 0),
        argumentSet("number 154", 154),
        argumentSet("number 916", 916),
        argumentSet("number 68504", 68504),
        argumentSet("number 76694", 76694),
        argumentSet("number 2186010", 2186010),
        argumentSet("number 2186011", 2186011),
        argumentSet("a number no member has as its value", 2199999));
  }

  static Stream<Arguments> unplacedActorTypeNumbers() {
    return Stream.of(
        argumentSet("number 921", 921),
        argumentSet("number 2962", 2962),
        argumentSet("number 5011", 5011),
        argumentSet("number 65792", 65792),
        argumentSet("number 70552", 70552),
        argumentSet("number 74646", 74646),
        argumentSet("number 199579", 199579),
        argumentSet("number 2183962", 2183962),
        argumentSet("number 2183963", 2183963),
        argumentSet("number 4194460", 4194460));
  }

  @ParameterizedTest
  @MethodSource("placedActorTypeNumbers")
  void anActorTypeNumberAnEarlyProtocolPlacesSurvivesBothConversions(int number) {
    assertEquals(
        number, ActorTypeNumbering.toNumber(729, ActorTypeNumbering.fromNumber(729, number)));
  }

  @ParameterizedTest
  @MethodSource("unplacedActorTypeNumbers")
  void anActorTypeNumberAnEarlyProtocolCannotPlaceDoesNotDecode(int number) {
    assertFalse(ActorTypeNumbering.decodes(729, number));
  }

  @Test
  void anActorTypeNumberNoMemberHasAsItsValueIsItsOwnValue() {
    assertEquals(2199999, ActorTypeNumbering.fromNumber(729, 2199999));
  }
}
