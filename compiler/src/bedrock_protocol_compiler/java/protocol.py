from functools import partial

from bedrock_protocol_compiler.java import names
from bedrock_protocol_compiler.java.enum import EnumGenerator
from bedrock_protocol_compiler.java.message import MessageGenerator
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import Schema


def definition(schema: Schema, generators: list[MessageGenerator | EnumGenerator], p: Printer) -> None:
    p.emit(
        """
        public enum $name$ {
            $constants$

            private final int version;
            private final @NotNull IntFunction<@Nullable Class<? extends Packet>> packets;

            $name$(int version, @NotNull IntFunction<@Nullable Class<? extends Packet>> packets) {
                this.version = version;
                this.packets = packets;
            }

            public int version() {
                return version;
            }

            public static @NotNull Optional<$name$> of(int number) {
                return $table$.of(number).map(version -> valueOf("v" + version.snapshot()));
            }

            public static @NotNull Optional<$name$> of(@NotNull String release) {
                return $table$.of(release).map(version -> valueOf("v" + version.snapshot()));
            }

            public byte @NotNull [] encode(@NotNull Message value) {
                ByteBuf buf = Unpooled.buffer();
                try {
                    encode(value, buf, $mode$.DEFAULT);
                    return ByteBufUtil.getBytes(buf);
                } finally {
                    buf.release();
                }
            }

            public byte @NotNull [] encode(@NotNull Message value, @NotNull $mode$ mode) {
                ByteBuf buf = Unpooled.buffer();
                try {
                    encode(value, buf, mode);
                    return ByteBufUtil.getBytes(buf);
                } finally {
                    buf.release();
                }
            }

            public void encode(@NotNull Message value, @NotNull ByteBuf buf) {
                encode(value, buf, $mode$.DEFAULT);
            }

            public void encode(@NotNull Message value, @NotNull ByteBuf buf, @NotNull $mode$ mode) {
                Registration<?> registration = Registry.TYPES.get(value.getClass());
                if (registration == null) {
                    throw new IllegalArgumentException(
                            value.getClass().getName() + ": is not a type at protocol " + version);
                }
                registration.encode(value, buf, version, mode);
            }

            public <T extends Message> @NotNull T decode(@NotNull Class<T> type, byte @NotNull [] data) {
                return decode(type, Unpooled.wrappedBuffer(data), $mode$.DEFAULT);
            }

            public <T extends Message> @NotNull T decode(
                    @NotNull Class<T> type, byte @NotNull [] data, @NotNull $mode$ mode) {
                return decode(type, Unpooled.wrappedBuffer(data), mode);
            }

            public <T extends Message> @NotNull T decode(@NotNull Class<T> type, @NotNull ByteBuf buf) {
                return decode(type, buf, $mode$.DEFAULT);
            }

            public <T extends Message> @NotNull T decode(
                    @NotNull Class<T> type, @NotNull ByteBuf buf, @NotNull $mode$ mode) {
                Registration<?> registration = Registry.TYPES.get(type);
                if (registration == null) {
                    throw new IllegalArgumentException(
                            type.getName() + ": is not a type at protocol " + version);
                }
                return type.cast(registration.decode(buf, version, mode));
            }

            public byte @NotNull [] encodePacket(@NotNull Packet packet) {
                ByteBuf buf = Unpooled.buffer();
                try {
                    encodePacket(packet, buf, 0, 0);
                    return ByteBufUtil.getBytes(buf);
                } finally {
                    buf.release();
                }
            }

            public byte @NotNull [] encodePacket(@NotNull Packet packet, int recipientSubId, int senderSubId) {
                ByteBuf buf = Unpooled.buffer();
                try {
                    encodePacket(packet, buf, recipientSubId, senderSubId);
                    return ByteBufUtil.getBytes(buf);
                } finally {
                    buf.release();
                }
            }

            public void encodePacket(@NotNull Packet packet, @NotNull ByteBuf buf) {
                encodePacket(packet, buf, 0, 0);
            }

            public void encodePacket(
                    @NotNull Packet packet, @NotNull ByteBuf buf, int recipientSubId, int senderSubId) {
                if (packets.apply(packet.getPacketId()) != packet.getClass()) {
                    throw new IllegalArgumentException(
                            "packet: " + packet.getClass().getName() + " is not a packet at protocol " + version);
                }
                new PacketHeader(packet.getPacketId(), recipientSubId, senderSubId).encode(buf);
                encode(packet, buf);
            }

            public @NotNull DecodedPacket decodePacket(byte @NotNull [] data) {
                return decodePacket(Unpooled.wrappedBuffer(data));
            }

            public @NotNull DecodedPacket decodePacket(@NotNull ByteBuf buf) {
                return ByteBufCodec.decode(buf, "PacketHeader", frame -> {
                    PacketHeader header = PacketHeader.decode(frame);
                    Class<? extends Packet> type = packets.apply(header.packetId());
                    if (type == null) {
                        throw DecodeException.unknownValue(frame.readerIndex()).prepend("packet_id");
                    }
                    return new DecodedPacket(header, decode(type, frame));
                });
            }

            $tables$

            private static final class Registry {
                private static final @NotNull Map<Class<? extends Message>, Registration<?>> TYPES = new HashMap<>();

                static {
                    $registrations$
                }

                private Registry() {}

                private static <T extends Message> void register(
                        @NotNull Class<T> type, @NotNull String name, @NotNull Selector<T> selector) {
                    TYPES.put(type, new Registration<>(type, name, selector));
                }
            }

            private interface Selector<T extends Message> {
                @NotNull Codec<T> codec(int version, @NotNull $mode$ mode);
            }

            private record Registration<T extends Message>(
                    @NotNull Class<T> type, @NotNull String name, @NotNull Selector<T> selector) {
                void encode(@NotNull Message value, @NotNull ByteBuf buf, int version, @NotNull $mode$ mode) {
                    selector.codec(version, mode).encode(type.cast(value), buf);
                }

                @NotNull T decode(@NotNull ByteBuf buf, int version, @NotNull $mode$ mode) {
                    return ByteBufCodec.decode(buf, name, selector.codec(version, mode));
                }
            }
        }
        """,
        name=names.PROTOCOL,
        table=names.VERSION,
        mode=names.MODE,
        constants=partial(constants, schema, p),
        registrations=partial(registrations, schema, p, generators),
        tables=partial(tables, schema, p),
    )


def constants(schema: Schema, p: Printer) -> None:
    for index, number in enumerate(schema.versions, 1):
        p.emit(
            "v$number$($number$, $name$::packets$number$)$end$",
            number=number,
            name=names.PROTOCOL,
            end="," if index < len(schema.versions) else ";",
        )


def registrations(schema: Schema, p: Printer, generators: list[MessageGenerator | EnumGenerator]) -> None:
    for generator in generators:
        if not isinstance(generator, MessageGenerator):
            continue
        if generator.codecs:
            p.emit(
                'register($spelled$.class, "$name$", $spelled$::codec);',
                spelled=generator.qualified,
                name=names.nested(schema, generator.model),
            )
        registrations(schema, p, generator.nested)


def tables(schema: Schema, p: Printer) -> None:
    for number in schema.versions:
        p.emit(
            """
            private static @Nullable Class<? extends Packet> packets$number$(int packetId) {
                return switch (packetId) {
                    $cases$
                    default -> null;
                };
            }

            """,
            number=number,
            cases=partial(cases, schema, p, number),
        )


def cases(schema: Schema, p: Printer, number: int) -> None:
    for packet_id, encoding in sorted(schema.packets(number).items()):
        p.emit("case $id$ -> $spelled$.class;", id=packet_id, spelled=names.qualified(schema, encoding.model))
