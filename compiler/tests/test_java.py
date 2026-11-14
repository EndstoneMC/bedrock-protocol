import pytest

from bedrock_protocol_compiler.__main__ import main

HEADER = """
import uuid
from enum import IntEnum
from typing import Literal
from protocol import (
    array, bitset, builtin, double, field, int16, packet, sentinel, type, uint8, uint16, uint32, uvarint32, uvarint64,
    value,
)
package = "bedrock.protocol"
java_package = "dev.endstone.protocol"
"""

INIT_135 = """
from bedrock_protocol_compiler.dsl import (
    array, bitset, builtin, double, field, int16, packet, sentinel, type, uint8, uint16, uint32, uvarint32, uvarint64,
    value,
)
versions = (1, 3, 5)
releases = {1: "1.1.0", 2: "1.2.0", 3: "1.3.0", 4: "1.4.0", 5: "1.5.x"}
"""

SCALAR = """
@packet(id=7)
class P:
    x: uint8
"""

COLORS = """
class Color(IntEnum, uint8):
    RED = 1
    CRIMSON = RED
    BLUE = value(2, deprecated=True)
"""


@pytest.fixture
def java(build_package, tmp_path):
    def run(source: str):
        build_package({"a": HEADER + source})
        main([str(tmp_path / "protocol"), "--java-out", str(tmp_path / "java")])
        return tmp_path / "java/dev/endstone/protocol"

    return run


@pytest.fixture
def emitted(java):
    def read(source: str, path: str = "P.java") -> str:
        return (java(source) / path).read_text()

    return read


def test_java_out_writes_a_file_per_top_level_shape(java):
    root = java(SCALAR + "class S:\n    class N:\n        x: uint8\n    n: N\n")

    assert {path.name for path in root.glob("*.java")} - {"Packets.java", "ProtocolVersion.java"} == {
        "P.java",
        "S.java",
    }


def test_java_out_writes_a_registry_per_version(java):
    root = java(SCALAR)

    assert sorted(path.relative_to(root).as_posix() for path in root.glob("v*/Packets.java")) == [
        "v1/Packets.java",
        "v2/Packets.java",
        "v3/Packets.java",
        "v4/Packets.java",
        "v5/Packets.java",
    ]


def test_java_out_writes_a_bare_registry(java):
    assert (java(SCALAR) / "Packets.java").is_file()


def test_java_out_writes_the_version_table(java):
    assert (java(SCALAR) / "ProtocolVersion.java").is_file()


def test_out_alone_writes_no_java_tree(build_package, tmp_path):
    build_package({"a": HEADER + SCALAR})

    main([str(tmp_path / "protocol"), "--out", str(tmp_path / "out")])

    assert sorted(path.name for path in tmp_path.iterdir()) == ["out", "protocol"]


def test_both_outputs_come_from_one_run(build_package, tmp_path):
    build_package({"a": HEADER + SCALAR})

    main([str(tmp_path / "protocol"), "--out", str(tmp_path / "out"), "--java-out", str(tmp_path / "java")])

    assert (tmp_path / "out/bedrock/protocol/a.h").is_file()
    assert (tmp_path / "java/dev/endstone/protocol/P.java").is_file()


def test_no_output_directory_is_a_usage_error(build_package, tmp_path, capsys):
    build_package({"a": HEADER + SCALAR})

    with pytest.raises(SystemExit, match=r"^2$"):
        main([str(tmp_path / "protocol")])

    assert "one of --out and --java-out is required" in capsys.readouterr().err


def test_a_java_error_writes_neither_output(build_package, tmp_path):
    build_package({"a": HEADER + "class Message:\n    x: uint8\n"})

    with pytest.raises(SystemExit, match=r"bpc: dev\.endstone\.protocol\.Message: shadows the imported Message"):
        main([str(tmp_path / "protocol"), "--out", str(tmp_path / "out"), "--java-out", str(tmp_path / "java")])

    assert sorted(path.name for path in tmp_path.iterdir()) == ["protocol"]


@pytest.mark.parametrize(
    ("source", "path"),
    [
        pytest.param("class S:\n    x: uint8\n", "S.java", id="unversioned"),
        pytest.param("@type(since=3)\nclass S:\n    x: uint8\n", "S.java", id="live-at-latest"),
        pytest.param("@type(since=2, until=4)\nclass S:\n    x: uint8\n", "v2/S.java", id="older-since"),
        pytest.param("@type(until=3)\nclass S:\n    x: uint8\n", "base/S.java", id="first-range-has-no-since"),
        pytest.param(
            "class S:\n    x: uint8\n\n@type(cereal=False)\nclass S:\n    x: uint16\n",
            "precereal/S.java",
            id="pre-cereal",
        ),
        pytest.param(
            "class S:\n    x: uint8\n\n@type(cereal=False, since=2, until=4)\nclass S:\n    x: uint16\n",
            "precereal/v2/S.java",
            id="older-pre-cereal",
        ),
    ],
)
def test_a_shape_lands_in_the_package_of_its_scope(java, source, path):
    assert (java(source) / path).is_file()


TWO_SHAPES = "@type(since=2, until=4)\nclass S:\n    x: uint8\n\n@type(since=4)\nclass S:\n    x: uint16\n"


def test_the_latest_of_two_shapes_is_bare(java):
    assert "    private final int x_;\n" in (java(TWO_SHAPES) / "S.java").read_text()


def test_the_older_of_two_shapes_keeps_its_since(java):
    assert "package dev.endstone.protocol.v2;\n" in (java(TWO_SHAPES) / "v2/S.java").read_text()


NESTED = "class P:\n    class N:\n        x: uint8\n    n: N\n    y: uint8 = field(since=3)\n"


def test_a_nested_shape_is_defined_in_its_newest_owner(java):
    assert "    public static final class N implements Message {\n" in (java(NESTED) / "P.java").read_text()


def test_a_nested_shape_is_not_defined_in_an_older_owner(java):
    assert "class N" not in (java(NESTED) / "base/P.java").read_text()


def test_an_older_owner_names_a_nested_shape_in_its_newest_owner(java):
    assert "    private final dev.endstone.protocol.P.N n_;\n" in (java(NESTED) / "base/P.java").read_text()


def test_a_nested_shape_is_a_static_nested_class_of_its_owner(emitted):
    text = emitted("class P:\n    class N:\n        x: uint8\n    n: N\n")

    assert "    public static final class N implements Message {\n" in text


def test_a_shape_reaches_another_by_its_qualified_name(emitted):
    text = emitted(
        "@type(since=2, until=4)\nclass S:\n    x: uint8\n\nclass P:\n    s: S = field(since=2, until=4)\n", "v2/P.java"
    )

    assert "private final dev.endstone.protocol.v2.S s_;" in text


def test_an_owner_of_only_nested_shapes_is_a_holder_class(emitted):
    text = emitted("class P:\n    class N:\n        x: uint8\n")

    assert "public final class P {\n    private P() {}\n\n    public static final class N implements Message {" in text


def test_a_packet_implements_packet_with_its_id(emitted):
    text = emitted(SCALAR)

    assert "public final class P implements Packet {\n    public static final int ID = 7;\n" in text


def test_a_packet_returns_its_id_from_get_packet_id(emitted):
    text = emitted(SCALAR)

    assert "    @Override\n    public int getPacketId() {\n        return ID;\n    }\n" in text


def test_the_registry_decodes_each_live_packet_by_id(java):
    text = (java(SCALAR + "@packet(id=3, since=2)\nclass Q:\n    x: uint8\n") / "v2/Packets.java").read_text()

    cases = (
        '            case 3 -> ByteBufCodec.decode(buf, "Q", dev.endstone.protocol.Q::decode);\n'
        '            case 7 -> ByteBufCodec.decode(buf, "P", dev.endstone.protocol.P::decode);\n'
    )
    assert cases in text


def test_the_registry_stamps_an_unknown_packet_id_as_the_packet_header(java):
    text = (java(SCALAR) / "v2/Packets.java").read_text()

    default = (
        '            default -> ByteBufCodec.decode(buf, "PacketHeader", body -> {\n'
        '                throw DecodeException.unknownValue(body.readerIndex()).prepend("packet_id");\n'
        "            });\n"
    )
    assert default in text


def test_the_bare_registry_decodes_as_the_latest_does(java):
    root = java(SCALAR + "@packet(id=3, until=4)\nclass Q:\n    x: uint8\n")

    assert (root / "Packets.java").read_text() == (root / "v5/Packets.java").read_text().replace(
        "package dev.endstone.protocol.v5;\n\nimport dev.endstone.protocol.ByteBufCodec;\n"
        "import dev.endstone.protocol.DecodeException;\nimport dev.endstone.protocol.Packet;\n",
        "package dev.endstone.protocol;\n\n",
    )


def test_the_bare_registry_leaves_out_a_packet_the_latest_lacks(java):
    text = (java(SCALAR + "@packet(id=3, until=4)\nclass Q:\n    x: uint8\n") / "Packets.java").read_text()

    assert '"Q"' not in text


def test_the_version_table_lists_the_versions(java):
    text = (java(SCALAR) / "ProtocolVersion.java").read_text()

    assert "    public static final @NotNull List<Integer> VERSIONS = List.of(1, 2, 3, 4, 5);\n" in text


def test_the_version_table_names_the_latest_version(java):
    text = (java(SCALAR) / "ProtocolVersion.java").read_text()

    assert "    public static final int LATEST_VERSION = 5;\n" in text


def test_a_release_takes_the_newest_version_at_or_below_its_number_as_its_snapshot(build_package, tmp_path):
    build_package({"a": HEADER + SCALAR}, INIT_135)

    main([str(tmp_path / "protocol"), "--java-out", str(tmp_path / "java")])

    text = (tmp_path / "java/dev/endstone/protocol/ProtocolVersion.java").read_text()
    releases = (
        "    public static final @NotNull List<ProtocolVersion> RELEASES = List.of(\n"
        '            new ProtocolVersion(1, 1, "1.1.0", "1.1.0", "1.1.0"),\n'
        '            new ProtocolVersion(2, 1, "1.2.0", "1.2.0", "1.2.0"),\n'
        '            new ProtocolVersion(3, 3, "1.3.0", "1.3.0", "1.3.0"),\n'
        '            new ProtocolVersion(4, 3, "1.4.0", "1.4.0", "1.4.0"),\n'
        '            new ProtocolVersion(5, 5, "1.5.x", "1.5.0", "1.5.9"));\n'
    )
    assert releases in text


def test_a_version_decodes_a_packet_with_the_registry_of_its_snapshot(java):
    text = (java(SCALAR) / "ProtocolVersion.java").read_text()

    cases = (
        "        return switch (snapshot) {\n"
        "            case 1 -> dev.endstone.protocol.v1.Packets.decode(packetId, buf);\n"
        "            case 2 -> dev.endstone.protocol.v2.Packets.decode(packetId, buf);\n"
        "            case 3 -> dev.endstone.protocol.v3.Packets.decode(packetId, buf);\n"
        "            case 4 -> dev.endstone.protocol.v4.Packets.decode(packetId, buf);\n"
        "            case 5 -> dev.endstone.protocol.v5.Packets.decode(packetId, buf);\n"
        "            default -> throw new IllegalStateException("
    )
    assert cases in text


def test_a_release_name_is_matched_between_first_and_last(java):
    text = (java(SCALAR) / "ProtocolVersion.java").read_text()

    match = (
        "            if (Arrays.compare(parse(version.first), wanted) <= 0\n"
        "                    && Arrays.compare(wanted, parse(version.last)) <= 0) {\n"
    )
    assert match in text


@pytest.mark.parametrize(
    "check",
    [
        pytest.param("if (i > 0 && (cursor == end || text.charAt(cursor++) != '.')) {", id="separator"),
        pytest.param("boolean negative = cursor < end && text.charAt(cursor) == '-';", id="sign"),
        pytest.param("long limit = negative ? -(long) Integer.MIN_VALUE : Integer.MAX_VALUE;", id="range"),
        pytest.param("if (cursor == digits) {", id="digits"),
        pytest.param("if (cursor != end) {", id="whole"),
    ],
)
def test_a_release_name_parses_as_from_chars_does(java, check):
    assert check in (java(SCALAR) / "ProtocolVersion.java").read_text()


def test_a_shape_named_like_the_version_table_is_a_compiler_error(build_package, tmp_path):
    build_package({"a": HEADER + "class ProtocolVersion:\n    x: uint8\n"})

    with pytest.raises(SystemExit, match=r"dev\.endstone\.protocol\.ProtocolVersion: is the protocol version table"):
        main([str(tmp_path / "protocol"), "--java-out", str(tmp_path / "java")])


def test_a_shape_named_like_the_bare_registry_is_a_compiler_error(build_package, tmp_path):
    build_package({"a": HEADER + "class Packets:\n    x: uint8\n"})

    with pytest.raises(SystemExit, match=r"dev\.endstone\.protocol\.Packets: is the packet registry of 5"):
        main([str(tmp_path / "protocol"), "--java-out", str(tmp_path / "java")])


def test_a_file_imports_only_what_it_names_outside_its_package(emitted):
    text = emitted(SCALAR)

    assert text.startswith(
        "package dev.endstone.protocol;\n\n"
        "import io.netty.buffer.ByteBuf;\n"
        "import org.jetbrains.annotations.NotNull;\n"
        "import org.jetbrains.annotations.Nullable;\n\n"
    )


def test_an_accessor_upper_cases_the_letter_after_a_digit(emitted):
    text = emitted("class P:\n    pos_2d_x: uint8\n")

    assert "public int getPos2DX() {" in text


@pytest.mark.parametrize(
    ("source", "message"),
    [
        pytest.param(
            "class P:\n    class_: uint8\n",
            r"P\.getClass: is generated for both java\.lang\.Object and class",
            id="object",
        ),
        pytest.param(
            "class P:\n    a_list: uint8\n    a: list[uint8]\n",
            r"P\.getAList: is generated for both a_list and a",
            id="field",
        ),
        pytest.param(
            "class P:\n    class List:\n        x: uint8\n", r"P\.List: shadows the imported List", id="import"
        ),
        pytest.param(
            "@packet(id=7)\nclass P:\n    packet_id: uint8\n",
            r"P\.getPacketId: is generated for both dev\.endstone\.protocol\.Packet and packet_id",
            id="packet-id",
        ),
        pytest.param(
            "class P:\n    default_instance: uint8\n",
            r"P\.getDefaultInstance: is generated for both P and default_instance",
            id="default-instance",
        ),
        pytest.param(
            "class P:\n    x: list[uint8]\n    all_x: list[uint8]\n",
            r"P\.Builder\.addAllX: is generated for both x and all_x",
            id="builder",
        ),
        pytest.param(
            "class MessageOnly:\n    x: uint8\n\nclass P:\n    body: MessageOnly | uint8\n    message_only: uint8\n",
            r"P\.getMessageOnly: is generated for both body\.message_only and message_only",
            id="union-case",
        ),
        pytest.param(
            "class P:\n    v: uint8 | str\n    v_case: uint8\n",
            r"P\.vCase_: is generated for both v and v_case",
            id="union-selector",
        ),
        pytest.param(
            "@packet(id=7)\nclass P:\n    id: Literal[True]\n",
            r"P\.ID: is generated for both P and id",
            id="literal-id",
        ),
        pytest.param(
            "class P:\n    default_instance: Literal[True]\n",
            r"P\.DEFAULT_INSTANCE: is generated for both P and default_instance",
            id="literal-default-instance",
        ),
    ],
)
def test_a_name_clash_is_a_compiler_error(build_package, tmp_path, source, message):
    build_package({"a": HEADER + source})

    with pytest.raises(SystemExit, match=message):
        main([str(tmp_path / "protocol"), "--java-out", str(tmp_path / "java")])


@pytest.mark.parametrize(
    ("source", "accessor"),
    [
        pytest.param("x: uint32", "public @NotNull Builder setX(int value) {", id="scalar"),
        pytest.param("x: uint32 | None", "public boolean hasX() {", id="optional"),
        pytest.param(
            "x: list[uint32]",
            "public @NotNull Builder addAllX(@NotNull Iterable<? extends Integer> values) {",
            id="list",
        ),
        pytest.param("x: dict[str, uint32]", "public int getXOrThrow(@NotNull String key) {", id="map"),
        pytest.param("x: Color", "public int getXValue() {", id="integer-coded-enum"),
    ],
)
def test_each_field_kind_has_its_accessors(emitted, source, accessor):
    assert accessor in emitted(COLORS + f"class P:\n    {source}\n")


def test_an_optional_reads_its_default_when_absent(emitted):
    text = emitted("class P:\n    x: uint32 | None\n")

    assert "return x_ == null ? 0 : x_;" in text


def test_an_array_builder_starts_with_its_size_in_defaults(emitted):
    text = emitted("class P:\n    x: array[uint16, 3]\n")

    assert "x_ = new ArrayList<>(Collections.nCopies(3, 0));" in text


def test_an_array_builder_offers_no_add(emitted):
    text = emitted("class P:\n    x: array[uint16, 3]\n")

    assert "addX" not in text


def test_clearing_an_array_resets_every_element(emitted):
    text = emitted("class P:\n    x: array[uint16, 3]\n")

    clear = (
        "        public @NotNull Builder clearX() {\n"
        "            x_ = new ArrayList<>(Collections.nCopies(3, 0));\n"
        "            return this;\n"
    )
    assert clear in text


@pytest.mark.parametrize(
    ("key", "order"),
    [
        pytest.param("str", "new TreeMap<>(ByteBufCodec.STR_ORDER)", id="str"),
        pytest.param("uint32", "new TreeMap<>(Integer::compareUnsigned)", id="unsigned"),
        pytest.param("int16", "new TreeMap<>()", id="signed"),
        pytest.param("float", "new TreeMap<>((a, b) -> a < b ? -1 : b < a ? 1 : 0)", id="float"),
        pytest.param("double", "new TreeMap<>((a, b) -> a < b ? -1 : b < a ? 1 : 0)", id="double"),
    ],
)
def test_a_map_orders_its_keys_as_std_map_does(emitted, key, order):
    assert order in emitted(f"class P:\n    x: dict[{key}, uint8]\n")


def test_a_narrow_setter_rejects_a_value_it_cannot_hold(emitted):
    text = emitted("class P:\n    x: uint8\n")

    reject = (
        "            if ((value & ~0xFF) != 0) {\n"
        '                throw new IllegalArgumentException("P.x: cannot hold " + value);\n'
    )
    assert reject in text


def test_a_mutable_value_is_copied_out_of_a_getter(emitted):
    text = emitted("class P:\n    x: bytes\n")

    assert "    public byte @NotNull [] getX() {\n        return x_.clone();\n" in text


def test_a_narrowing_read_fails_out_of_range(emitted):
    text = emitted("class P:\n    x: uint8 = field(type=uvarint64)\n")

    read = (
        "            long v0 = ByteBufCodec.readUnsignedVarLong(buf);\n"
        "            int s0 = (int) (v0 & 0xFF);\n"
        "            if ((long) s0 != v0) {\n"
        "                throw DecodeException.outOfRange(buf.readerIndex());\n"
    )
    assert read in text


def test_a_field_read_prepends_its_name_to_a_failure(emitted):
    text = emitted("class P:\n    some_x: uint8\n")

    assert 'throw e.prepend("some_x").setUnfinishedMessage(out.build());' in text


def test_a_list_reads_its_prefix_as_a_count(emitted):
    text = emitted("class P:\n    x: list[uint8] = field(prefix=uint16)\n")

    assert "int count0 = ByteBufCodec.toCount(buf, ByteBufCodec.readUint16Count(buf));" in text


def test_a_counted_list_takes_its_count_from_an_earlier_field(emitted):
    text = emitted("class P:\n    n: uint32\n    x: list[uint8] = field(count=lambda p: p.n)\n")

    assert "ByteBufCodec.toCount(buf, ByteBufCodec.countValue(buf, Integer.toUnsignedLong(out.n_)));" in text


def test_a_counted_list_writes_no_prefix(emitted):
    text = emitted("class P:\n    n: uint32\n    x: list[uint8] = field(count=lambda p: p.n)\n")

    assert "    public void encode(@NotNull ByteBuf buf) {\n        buf.writeIntLE(n_);\n        for (" in text


def test_an_optional_writes_its_presence_first(emitted):
    text = emitted("class P:\n    x: uint32 | None\n")

    assert "buf.writeBoolean(x_ != null);\n        if (x_ != null) {\n            buf.writeIntLE((int) x_);\n" in text


BITSET = "class W(IntEnum, uint8):\n    A = 0\n    COUNT = 9\n\nclass P:\n    x: bitset[W.COUNT]\n"


def test_a_bitset_writes_its_width(emitted):
    assert 'ByteBufCodec.writeBitSet(buf, x_, 9, "P.x");' in emitted(BITSET)


def test_a_bitset_setter_rejects_a_bit_past_its_width(emitted):
    reject = (
        "            if (value.length() > 9) {\n"
        '                throw new IllegalArgumentException("P.x: cannot hold bit " + (value.length() - 1));\n'
    )
    assert reject in emitted(BITSET)


def test_a_bound_field_reads_once_per_binding(emitted):
    text = emitted("class P:\n    x: uint8 = field(bind=['a', 'b'])\n")

    read = (
        "            for (int binding = 0; binding < 2; binding++) {\n"
        "                out.x_ = ByteBufCodec.readUnsignedByte(buf);\n"
        "            }\n"
    )
    assert read in text


def test_a_condition_groups_its_fields_in_one_block(emitted):
    text = emitted(
        "class P:\n    f: bool\n    a: uint8 = field(when=lambda p: p.f)\n    b: uint8 = field(when=lambda p: p.f)\n"
    )

    assert "        if (f_) {\n            buf.writeByte(a_);\n            buf.writeByte(b_);\n        }\n" in text


def test_an_unsigned_comparison_compares_unsigned(emitted):
    text = emitted("class P:\n    n: uint32\n    x: uint8 = field(when=lambda p: p.n < 5)\n")

    assert "if (Integer.compareUnsigned(n_, 5) < 0) {" in text


def test_an_unsigned_literal_past_int_is_spelled_as_bits(emitted):
    text = emitted("class P:\n    n: uint32\n    x: uint8 = field(when=lambda p: p.n == 4294967294)\n")

    assert "if ((n_) == (0xFFFFFFFE)) {" in text


def test_a_name_coded_enum_is_compared_by_its_number(emitted):
    text = emitted(
        COLORS + "class P:\n    c: Color = field(type=str)\n    x: uint8 = field(when=lambda p: p.c == Color.RED)\n"
    )

    assert "if ((c_.getNumber()) == (1)) {" in text


def test_a_literal_rejects_any_other_value(emitted):
    text = emitted(COLORS + "class P:\n    c: Literal[Color.BLUE]\n")

    assert "if (ByteBufCodec.readUnsignedByte(buf) != 2) {\n                throw DecodeException.unknownValue(" in text


def test_a_literal_is_no_field(emitted):
    text = emitted(COLORS + "class P:\n    c: Literal[Color.BLUE]\n")

    assert "c_" not in text


@pytest.mark.parametrize(
    ("source", "constant"),
    [
        pytest.param("flag: Literal[True]", "    public static final boolean FLAG = true;\n", id="bool"),
        pytest.param('tag: Literal["hi"]', '    public static final @NotNull String TAG = "hi";\n', id="str"),
        pytest.param(
            "c: Literal[Color.RED]",
            "    public static final @NotNull dev.endstone.protocol.Color C = dev.endstone.protocol.Color.RED;\n",
            id="enum",
        ),
    ],
)
def test_a_literal_is_a_public_constant_of_its_message(emitted, source, constant):
    assert constant in emitted(COLORS + f"class P:\n    {source}\n")


def test_an_enum_literal_names_the_canonical_constant_of_an_alias(emitted):
    text = emitted(COLORS + "class P:\n    c: Literal[Color.CRIMSON]\n")

    assert " C = dev.endstone.protocol.Color.RED;\n" in text


def test_an_enum_literal_of_a_live_constant_is_not_deprecated(emitted):
    assert "@Deprecated" not in emitted(COLORS + "class P:\n    c: Literal[Color.RED]\n")


def test_an_enum_literal_of_a_deprecated_constant_is_deprecated(emitted):
    text = emitted(COLORS + "class P:\n    c: Literal[Color.BLUE]\n")

    assert "    @Deprecated\n    public static final @NotNull dev.endstone.protocol.Color C = " in text


def test_an_enum_literal_of_a_deprecated_alias_is_deprecated(emitted):
    text = emitted(
        "class Hue(IntEnum, uint8):\n    A = 1\n    B = value(1, deprecated=True)\n\nclass P:\n    c: Literal[Hue.B]\n"
    )

    assert "    @Deprecated\n    public static final @NotNull dev.endstone.protocol.Hue C = " in text


def test_an_enum_literal_of_an_alias_of_a_deprecated_constant_is_deprecated(emitted):
    text = emitted(
        "class Hue(IntEnum, uint8):\n    A = value(1, deprecated=True)\n    B = A\n\nclass P:\n    c: Literal[Hue.B]\n"
    )

    assert "    @Deprecated\n    public static final @NotNull dev.endstone.protocol.Hue C = " in text


def test_an_underscored_marker_drops_its_underscores_from_its_constant_name(emitted):
    assert '    public static final @NotNull String RAW = "raw";\n' in emitted('class P:\n    _raw: Literal["raw"]\n')


def test_an_enum_literal_with_no_constant_is_a_compiler_error(build_package, tmp_path):
    source = "class W(IntEnum, uint8):\n    A = 0\n    COUNT = sentinel()\n\nclass P:\n    w: Literal[W.COUNT]\n"
    build_package({"a": HEADER + source})

    with pytest.raises(SystemExit, match=r"P\.w: W\.COUNT has no constant in dev\.endstone\.protocol\.W"):
        main([str(tmp_path / "protocol"), "--java-out", str(tmp_path / "java")])


def test_a_literal_named_only_by_underscores_is_a_compiler_error(build_package, tmp_path):
    build_package({"a": HEADER + "class P:\n    _: Literal[True]\n"})

    with pytest.raises(SystemExit, match=r"P\._: a literal needs a name besides underscores"):
        main([str(tmp_path / "protocol"), "--java-out", str(tmp_path / "java")])


def test_an_enum_has_a_constant_per_number(java):
    text = (java(COLORS) / "Color.java").read_text()

    assert "    RED(1),\n" in text
    assert "    BLUE(2),\n" in text


def test_an_enum_marks_a_deprecated_constant(java):
    assert "    @Deprecated\n    BLUE(2),\n" in (java(COLORS) / "Color.java").read_text()


def test_an_enum_ends_with_unrecognized(java):
    assert "    BLUE(2),\n    UNRECOGNIZED(-1);\n" in (java(COLORS) / "Color.java").read_text()


def test_an_enum_alias_is_a_static_of_its_canonical_constant(java):
    text = (java(COLORS) / "Color.java").read_text()

    assert "public static final @NotNull Color CRIMSON = RED;" in text


def test_a_name_coded_enum_writes_the_name_reflected_first(java):
    text = (java(COLORS + "class P:\n    c: Color = field(type=str)\n") / "Color.java").read_text()

    assert '            case RED -> "crimson";\n            case BLUE -> "blue";\n' in text


def test_a_name_coded_enum_decodes_every_encoded_name(java):
    text = (java(COLORS + "class P:\n    c: Color = field(type=str)\n") / "Color.java").read_text()

    assert (
        '            case "crimson" -> RED;\n            case "red" -> RED;\n            case "blue" -> BLUE;\n' in text
    )


def test_a_name_coded_enum_defaults_to_its_first_member(emitted):
    text = emitted(COLORS + "class P:\n    c: Color = field(type=str)\n")

    assert "c_ = dev.endstone.protocol.Color.RED;" in text


def test_a_union_has_a_case_per_alternative(emitted):
    text = emitted("class S:\n    x: uint8\n\nclass P:\n    v: S | list[uint8]\n")

    assert "    public enum VCase {\n        S,\n        UINT8_LIST\n    }\n" in text


def test_a_union_spells_none_as_its_not_set_case(emitted):
    text = emitted("class P:\n    v: uint8 | None | str\n")

    assert "    public enum VCase {\n        UINT8,\n        V_NOT_SET,\n        STR\n    }\n" in text


@pytest.mark.parametrize(
    "accessor",
    [
        pytest.param("    public @NotNull VCase getVCase() {\n", id="case"),
        pytest.param("    public boolean hasS() {\n", id="has"),
        pytest.param("    public @NotNull dev.endstone.protocol.S getS() {\n", id="get"),
    ],
)
def test_a_union_held_by_a_field_puts_its_accessors_on_the_holder(emitted, accessor):
    assert accessor in emitted("class S:\n    x: uint8\n\nclass P:\n    v: S | uint8\n")


@pytest.mark.parametrize(
    "accessor",
    [
        pytest.param("        public @NotNull VCase getVCase() {\n", id="case"),
        pytest.param("        public boolean hasS() {\n", id="has"),
        pytest.param("        public @NotNull Builder setS(@NotNull dev.endstone.protocol.S value) {\n", id="set"),
        pytest.param("        public @NotNull Builder clearV() {\n", id="clear"),
    ],
)
def test_a_union_held_by_a_field_puts_its_accessors_on_the_builder(emitted, accessor):
    assert accessor in emitted("class S:\n    x: uint8\n\nclass P:\n    v: S | uint8\n")


def test_a_union_held_by_a_field_has_no_wrapper_class(emitted):
    text = emitted("class P:\n    v: uint8 | str\n")

    assert "class V " not in text


def test_a_union_case_member_prefixes_the_case_name_with_the_field_name(emitted):
    text = emitted("class P:\n    v: uint8 | str\n")

    assert "    private final int vUint8_;\n    private final String vStr_;\n" in text


def test_a_union_selector_member_is_named_after_the_field(emitted):
    assert "    private final VCase vCase_;\n" in emitted("class P:\n    v: uint8 | str\n")


def test_a_union_in_a_list_keeps_its_wrapper(emitted):
    assert "    public static final class V implements Message {\n" in emitted("class P:\n    v: list[uint8 | str]\n")


def test_a_union_in_a_list_is_held_as_a_list_of_its_wrapper(emitted):
    assert "    private final List<V> v_;\n" in emitted("class P:\n    v: list[uint8 | str]\n")


def test_unions_sharing_a_case_name_keep_their_wrappers(emitted):
    text = emitted("class P:\n    v: uint8 | str\n    w: uint8 | bool\n")

    assert "    private final V v_;\n    private final W w_;\n" in text


def test_unions_with_distinct_case_names_are_both_held_by_the_message(emitted):
    text = emitted("class P:\n    v: uint8 | str\n    w: bool | uint16\n")

    assert "    public boolean hasUint8() {\n" in text
    assert "    public boolean hasUint16() {\n" in text


def test_a_union_defaults_to_its_first_case(emitted):
    text = emitted("class P:\n    v: uint8 | str\n")

    assert "        private Builder() {\n            vCase_ = VCase.UINT8;\n            vUint8_ = 0;\n" in text


def test_an_optional_union_defaults_to_its_first_case_as_a_cpp_variant_does(emitted):
    text = emitted("class P:\n    v: uint8 | str | None\n")

    assert "        private Builder() {\n            vCase_ = VCase.UINT8;\n" in text


def test_clearing_an_optional_union_selects_its_unset_case(emitted):
    text = emitted("class P:\n    v: uint8 | str | None\n")

    clear = (
        "        public @NotNull Builder clearV() {\n            vCase_ = VCase.V_NOT_SET;\n            return this;\n"
    )
    assert clear in text


def test_clearing_a_required_union_resets_its_first_case(emitted):
    text = emitted("class P:\n    v: uint8 | str\n")

    clear = (
        "        public @NotNull Builder clearV() {\n"
        "            vCase_ = VCase.UINT8;\n"
        "            vUint8_ = 0;\n"
        "            return this;\n"
    )
    assert clear in text


def test_a_union_getter_reads_the_default_unless_its_case_is_set(emitted):
    text = emitted("class P:\n    v: uint8 | str\n")

    assert '        return vCase_ == VCase.STR ? vStr_ : "";\n' in text


def test_a_union_setter_selects_its_case(emitted):
    text = emitted("class P:\n    v: uint8 | str\n")

    assert "            vStr_ = Objects.requireNonNull(value);\n            vCase_ = VCase.STR;\n" in text


def test_a_union_reads_into_the_case_it_selects(emitted):
    text = emitted("class P:\n    v: uint8 | str\n")

    read = (
        "            switch (ByteBufCodec.readUnsignedVarInt(buf)) {\n"
        "                case 0 -> {\n"
        "                    out.vUint8_ = ByteBufCodec.readUnsignedByte(buf);\n"
        "                    out.vCase_ = VCase.UINT8;\n"
        "                }\n"
    )
    assert read in text


def test_an_unknown_union_index_is_an_unknown_value(emitted):
    text = emitted("class P:\n    v: uint8 | str\n")

    assert "                default -> throw DecodeException.unknownValue(buf.readerIndex());\n" in text


def test_a_union_read_prepends_the_field_name_to_a_failure(emitted):
    text = emitted("class P:\n    v: uint8 | str\n")

    assert 'throw e.prepend("v").setUnfinishedMessage(out.build());' in text


def test_a_union_compares_its_case_then_its_values(emitted):
    text = emitted("class P:\n    v: uint8 | str\n")

    assert "        return vCase_ == other.vCase_\n                && vUint8_ == other.vUint8_\n" in text


def test_a_union_hashes_its_case_then_its_values(emitted):
    text = emitted("class P:\n    v: uint8 | str\n")

    hashes = (
        "        hash = 31 * hash + Integer.hashCode(vCase_.ordinal());\n"
        "        hash = 31 * hash + Integer.hashCode(vUint8_);\n"
    )
    assert hashes in text


def test_a_bound_union_is_held_by_the_message(emitted):
    text = emitted("class P:\n    v: uint8 | str = field(bind=['a', 'b'])\n")

    assert "    private final VCase vCase_;\n" in text


def test_a_bound_union_reads_once_per_binding(emitted):
    text = emitted("class P:\n    v: uint8 | str = field(bind=['a', 'b'])\n")

    read = (
        "            for (int binding = 0; binding < 2; binding++) {\n"
        "                switch (ByteBufCodec.readUnsignedVarInt(buf)) {\n"
    )
    assert read in text


def test_a_union_writes_its_index_first(emitted):
    text = emitted("class P:\n    v: uint8 | str\n")

    assert "ByteBufCodec.writeUnsignedVarInt(buf, vCase_.ordinal());" in text


def test_a_union_with_two_cases_of_one_name_is_a_compiler_error(build_package, tmp_path):
    build_package({"a": HEADER + "class P:\n    v: list[uint8] | list[uint8]\n"})

    with pytest.raises(SystemExit, match=r"VCase\.UINT8_LIST: is generated for both case 0 and case 1"):
        main([str(tmp_path / "protocol"), "--java-out", str(tmp_path / "java")])


@pytest.mark.parametrize(
    ("annotation", "read"),
    [
        pytest.param("uuid.UUID", "out.id_ = ByteBufCodec.readUuid(buf);", id="raw"),
        pytest.param("uuid.UUID = field(type=str)", "out.id_ = ByteBufCodec.readUuidString(buf);", id="str"),
    ],
)
def test_a_uuid_reads_by_its_encoding(emitted, annotation, read):
    assert read in emitted(f"class P:\n    id: {annotation}\n")


@pytest.mark.parametrize(
    ("annotation", "write"),
    [
        pytest.param("uuid.UUID", "ByteBufCodec.writeUuid(buf, id_);", id="raw"),
        pytest.param("uuid.UUID = field(type=str)", "ByteBufCodec.writeUuidString(buf, id_);", id="str"),
    ],
)
def test_a_uuid_writes_by_its_encoding(emitted, annotation, write):
    assert write in emitted(f"class P:\n    id: {annotation}\n")


def test_a_uuid_is_a_java_util_uuid(emitted):
    assert "import java.util.UUID;\n" in emitted("class P:\n    id: uuid.UUID\n")


def test_a_uuid_defaults_to_zero(emitted):
    assert "            id_ = new UUID(0L, 0L);\n" in emitted("class P:\n    id: uuid.UUID\n")


def test_a_uuid_is_not_copied(emitted):
    text = emitted("class P:\n    id: uuid.UUID\n")

    assert "    public @NotNull UUID getId() {\n        return id_;\n" in text


BUILTIN = "@builtin\nclass NBTThing:\n    pass\n\nclass P:\n    t: NBTThing\n"


def test_a_builtin_lives_in_its_module_package_without_underscores(build_package, tmp_path):
    build_package({"my_stuff": HEADER + BUILTIN})

    main([str(tmp_path / "protocol"), "--java-out", str(tmp_path / "java")])

    assert (
        "import dev.endstone.protocol.mystuff.NBTThing;\n"
        in (tmp_path / "java/dev/endstone/protocol/P.java").read_text()
    )


def test_a_builtin_reads_by_its_snake_cased_name(emitted):
    assert "out.t_ = ByteBufCodec.readNbtThing(buf);" in emitted(BUILTIN)


def test_a_builtin_writes_by_its_snake_cased_name(emitted):
    assert "ByteBufCodec.writeNbtThing(buf, t_);" in emitted(BUILTIN)


def test_a_builtin_defaults_to_its_default_instance(emitted):
    assert "            t_ = NBTThing.getDefaultInstance();\n" in emitted(BUILTIN)


def test_a_builtin_is_copied_out_of_a_getter(emitted):
    assert "    public @NotNull NBTThing getT() {\n        return t_.copy();\n" in emitted(BUILTIN)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        pytest.param("x: list[uint8 | None]", r"P\.x: an optional inside another type is not supported", id="optional"),
        pytest.param("x: list[dict[str, uint8]]", r"P\.x: a map inside another type is not supported", id="map"),
    ],
)
def test_a_kind_no_value_holds_is_a_compiler_error(build_package, tmp_path, source, message):
    build_package({"a": HEADER + f"class P:\n    {source}\n"})

    with pytest.raises(SystemExit, match=message):
        main([str(tmp_path / "protocol"), "--java-out", str(tmp_path / "java")])


def test_a_big_endian_width_the_runtime_lacks_is_a_compiler_error(build_package, tmp_path):
    build_package({"a": HEADER + "class P:\n    x: int16 = field(endian='big')\n"})

    with pytest.raises(SystemExit, match=r"P\.x: ByteBufCodec has no big-endian int16"):
        main([str(tmp_path / "protocol"), "--java-out", str(tmp_path / "java")])
