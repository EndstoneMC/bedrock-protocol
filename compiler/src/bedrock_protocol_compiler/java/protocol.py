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
        if generator.codecs:
            p.emit(
                'register($spelled$.class, "$name$", $spelled$::codec);',
                spelled=generator.qualified,
                name=names.nested(schema, generator.model),
            )
        registrations(schema, p, generator.nested)
