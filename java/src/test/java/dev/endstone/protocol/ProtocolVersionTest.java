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

    @Test
    void supportedVersionsAscendByProtocol() {
        List<Integer> protocols =
                ProtocolVersion.SUPPORTED_VERSIONS.stream()
                        .map(ProtocolVersion::getProtocol)
                        .toList();
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
    void anUnknownProtocolHasNoVersion() {
        assertTrue(ProtocolVersion.get(1).isEmpty());
    }
}
