package dev.endstone.protocol;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.params.provider.Arguments.argumentSet;

import com.google.gson.JsonParser;
import dev.endstone.protocol.nbt.ByteTag;
import dev.endstone.protocol.nbt.CompoundTag;
import dev.endstone.protocol.nbt.FloatTag;
import dev.endstone.protocol.nbt.IntTag;
import dev.endstone.protocol.nbt.ListTag;
import dev.endstone.protocol.nbt.StringTag;
import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

final class CaseLoaderTest {
    static Stream<Arguments> nonFiniteFloats() {
        return Stream.of(
                argumentSet("not a number", "NaN", Float.NaN),
                argumentSet("infinity", "Infinity", Float.POSITIVE_INFINITY),
                argumentSet("negative infinity", "-Infinity", Float.NEGATIVE_INFINITY));
    }

    static Stream<Arguments> nonFiniteDoubles() {
        return Stream.of(
                argumentSet("not a number", "NaN", Double.NaN),
                argumentSet("infinity", "Infinity", Double.POSITIVE_INFINITY),
                argumentSet("negative infinity", "-Infinity", Double.NEGATIVE_INFINITY));
    }

    @Test
    void snbtReadsTypedScalars() {
        CompoundTag expected = new CompoundTag();
        expected.put("b", ByteTag.valueOf((byte) 1));
        expected.put("f", FloatTag.valueOf(1.5f));
        expected.put("i", IntTag.valueOf(7));
        expected.put("s", StringTag.valueOf("00000007"));
        assertEquals(expected, CaseLoader.Snbt.parse("{b:1b,f:1.5f,i:7,s:\"00000007\"}"));
    }

    @Test
    void snbtReadsNestedLists() {
        CompoundTag entry = new CompoundTag();
        entry.put("id", IntTag.valueOf(7));
        CompoundTag expected = new CompoundTag();
        expected.put("list", new ListTag(List.of(entry)));
        assertEquals(expected, CaseLoader.Snbt.parse("{list:[{id:7}]}"));
    }

    @Test
    void snbtReadsAnEmptyCompound() {
        assertEquals(new CompoundTag(), CaseLoader.Snbt.parse("{}"));
    }

    @Test
    void snbtReadsAnEmptyList() {
        CompoundTag expected = new CompoundTag();
        expected.put("list", new ListTag());
        assertEquals(expected, CaseLoader.Snbt.parse("{list:[]}"));
    }

    @Test
    void snbtRejectsTrailingText() {
        assertEquals(
                "SNBT at 2: trailing text in {}x",
                assertThrows(IllegalArgumentException.class, () -> CaseLoader.Snbt.parse("{}x"))
                        .getMessage());
    }

    @ParameterizedTest
    @MethodSource("nonFiniteFloats")
    void aNonFiniteNameLoadsIntoAFloatField(String name, float expected)
            throws ReflectiveOperationException {
        ChangeMobPropertyPacket packet =
                CaseLoader.load(
                        ProtocolVersion.LATEST_VERSION,
                        ChangeMobPropertyPacket.class,
                        JsonParser.parseString(
                                "{\"actor_id\":0,\"prop_name\":\"\",\"bool_component_val\":false,"
                                        + "\"string_component_val\":\"\",\"int_component_val\":0,"
                                        + "\"float_component_val\":\""
                                        + name
                                        + "\"}"));
        assertEquals(expected, packet.getFloatComponentVal());
    }

    @ParameterizedTest
    @MethodSource("nonFiniteDoubles")
    void aNonFiniteNameLoadsIntoADoubleArm(String name, double expected)
            throws ReflectiveOperationException {
        DataStoreUpdate update =
                CaseLoader.load(
                        ProtocolVersion.LATEST_VERSION,
                        DataStoreUpdate.class,
                        JsonParser.parseString(
                                "{\"data_store_name\":\"\",\"property\":\"\",\"path\":\"\","
                                        + "\"data\":\""
                                        + name
                                        + "\",\"property_update_count\":0,"
                                        + "\"path_update_count\":0}"));
        assertEquals(expected, update.getDouble());
    }

    @Test
    void notANumberLoadsAsTheFloatArmOfAFloatOrStringUnion() throws ReflectiveOperationException {
        ServerboundPackSettingChangePacket packet =
                CaseLoader.load(
                        ProtocolVersion.LATEST_VERSION,
                        ServerboundPackSettingChangePacket.class,
                        JsonParser.parseString(
                                "{\"pack_id\":\"00000000-0000-0000-0000-000000000000\","
                                        + "\"setting_name\":\"\",\"setting_value\":\"NaN\"}"));
        assertEquals(
                ServerboundPackSettingChangePacket.SettingValueCase.FLOAT,
                packet.getSettingValueCase());
    }

    @Test
    void anOrdinaryStringLoadsAsTheStringArmOfAFloatOrStringUnion()
            throws ReflectiveOperationException {
        ServerboundPackSettingChangePacket packet =
                CaseLoader.load(
                        ProtocolVersion.LATEST_VERSION,
                        ServerboundPackSettingChangePacket.class,
                        JsonParser.parseString(
                                "{\"pack_id\":\"00000000-0000-0000-0000-000000000000\","
                                        + "\"setting_name\":\"\",\"setting_value\":\"high\"}"));
        assertEquals(
                ServerboundPackSettingChangePacket.SettingValueCase.STR,
                packet.getSettingValueCase());
    }

    @Test
    void aPlainEnumInItsEncodedRangeLoadsAsItsDeclaredMember() throws ReflectiveOperationException {
        ContainerClosePacket packet =
                CaseLoader.load(
                        ProtocolVersion.LATEST_VERSION,
                        ContainerClosePacket.class,
                        JsonParser.parseString(
                                "{\"container_id\":255,\"container_type\":0,"
                                        + "\"server_initiated_close\":false}"));
        assertEquals(ContainerID.NONE, packet.getContainerId());
    }
}
