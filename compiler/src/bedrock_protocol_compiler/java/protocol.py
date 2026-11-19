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

            $name$(int version) {
                this.version = version;
            }

            public int version() {
                return version;
            }

            public static @NotNull $name$ latest() {
                return v$latest$;
            }

            public byte @NotNull [] encode(@NotNull Packet packet) {
                ByteBuf buf = Unpooled.buffer();
                try {
                    encode(packet, buf);
                    return ByteBufUtil.getBytes(buf);
                } finally {
                    buf.release();
                }
            }

            public void encode(@NotNull Packet packet, @NotNull ByteBuf buf) {
                Registration<?> registration = Registry.TYPES.get(packet.getClass());
                if (registration == null) {
                    throw new IllegalArgumentException(
                            packet.getClass().getName() + ": is not a type at protocol " + version);
                }
                registration.encode(packet, buf, version);
            }

            public <T extends Packet> @NotNull T decode(@NotNull Class<T> type, byte @NotNull [] data) {
                return decode(type, Unpooled.wrappedBuffer(data));
            }

            public <T extends Packet> @NotNull T decode(@NotNull Class<T> type, @NotNull ByteBuf buf) {
                Registration<?> registration = Registry.TYPES.get(type);
                if (registration == null) {
                    throw new IllegalArgumentException(
                            type.getName() + ": is not a type at protocol " + version);
                }
                return type.cast(registration.decode(buf, version));
            }

            private static final class Registry {
                private static final @NotNull Map<Class<? extends Packet>, Registration<?>> TYPES = new HashMap<>();

                static {
                    $registrations$
                }

                private Registry() {}

                private static <T extends Packet> void register(
                        @NotNull Class<T> type, @NotNull String name, @NotNull Selector<T> selector) {
                    TYPES.put(type, new Registration<>(type, name, selector));
                }
            }

            private interface Selector<T extends Packet> {
                @NotNull Codec<T> codec(int version);
            }

            private record Registration<T extends Packet>(
                    @NotNull Class<T> type, @NotNull String name, @NotNull Selector<T> selector) {
                void encode(@NotNull Packet packet, @NotNull ByteBuf buf, int version) {
                    selector.codec(version).encode(type.cast(packet), buf);
                }

                @NotNull T decode(@NotNull ByteBuf buf, int version) {
                    return ByteBufCodec.decode(buf, name, selector.codec(version));
                }
            }
        }
        """,
        name=names.PROTOCOL,
        latest=schema.latest,
        constants=partial(constants, schema, p),
        registrations=partial(registrations, schema, p, generators),
    )


def constants(schema: Schema, p: Printer) -> None:
    for index, number in enumerate(schema.versions, 1):
        p.emit(
            "v$number$($number$)$end$",
            number=number,
            end="," if index < len(schema.versions) else ";",
        )


def registrations(schema: Schema, p: Printer, generators: list[MessageGenerator | EnumGenerator]) -> None:
    for generator in generators:
        if not isinstance(generator, MessageGenerator):
            continue
        if generator.packet_id is not None and generator.codecs:
            p.emit(
                'register($spelled$.class, "$name$", $spelled$::codec);',
                spelled=generator.qualified,
                name=names.nested(schema, generator.model),
            )
        registrations(schema, p, generator.nested)
