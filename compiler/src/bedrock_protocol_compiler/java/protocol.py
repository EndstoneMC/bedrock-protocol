from functools import partial

from bedrock_protocol_compiler.java import names
from bedrock_protocol_compiler.java.enum import EnumGenerator
from bedrock_protocol_compiler.java.message import MessageGenerator
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumModel, Schema


def definition(
    schema: Schema, generators: list[MessageGenerator | EnumGenerator], enums: list[EnumModel], p: Printer
) -> None:
    p.emit(
        """
        public final class $name$ {
            private $name$() {}

            public static byte @NotNull [] encode(@NotNull Packet packet) {
                return v$latest$.encode(packet);
            }

            public static void encode(@NotNull Packet packet, @NotNull ByteBuf buf) {
                v$latest$.encode(packet, buf);
            }

            public static <T extends Packet> @NotNull T decode(@NotNull Class<T> type, byte @NotNull [] data) {
                return v$latest$.decode(type, data);
            }

            public static <T extends Packet> @NotNull T decode(@NotNull Class<T> type, @NotNull ByteBuf buf) {
                return v$latest$.decode(type, buf);
            }

            $versions$
            private static byte @NotNull [] encode(int version, @NotNull Packet packet) {
                ByteBuf buf = Unpooled.buffer();
                try {
                    encode(version, packet, buf);
                    return ByteBufUtil.getBytes(buf);
                } finally {
                    buf.release();
                }
            }

            private static void encode(int version, @NotNull Packet packet, @NotNull ByteBuf buf) {
                Registration<?> registration = Registry.TYPES.get(packet.getClass());
                if (registration == null) {
                    throw new IllegalArgumentException(
                            packet.getClass().getName() + ": is not a type at protocol " + version);
                }
                registration.encode(packet, buf, version);
            }

            private static <T extends Packet> @NotNull T decode(
                    int version, @NotNull Class<T> type, byte @NotNull [] data) {
                return decode(version, type, Unpooled.wrappedBuffer(data));
            }

            private static <T extends Packet> @NotNull T decode(
                    int version, @NotNull Class<T> type, @NotNull ByteBuf buf) {
                Registration<?> registration = Registry.TYPES.get(type);
                if (registration == null) {
                    throw new IllegalArgumentException(
                            type.getName() + ": is not a type at protocol " + version);
                }
                return type.cast(registration.decode(buf, version));
            }

            private static <E extends Enum<E>> @NotNull OptionalInt enumInteger(int version, @NotNull E value) {
                return Enums.of(value.getDeclaringClass()).enumInteger(version, value);
            }

            private static <E extends Enum<E>> @NotNull Optional<E> enumCast(
                    int version, @NotNull Class<E> type, int number) {
                return Enums.of(type).cast().apply(version, number).map(type::cast);
            }

            private static <E extends Enum<E>> @NotNull List<E> enumValues(int version, @NotNull Class<E> type) {
                return Enums.of(type).values().apply(version).stream().map(type::cast).toList();
            }

            private static <E extends Enum<E>> @NotNull Optional<String> enumName(int version, @NotNull E value) {
                return Enums.named(value.getDeclaringClass()).enumName(version, value);
            }

            private static <E extends Enum<E>> @NotNull Optional<E> enumCast(
                    int version, @NotNull Class<E> type, @NotNull String name) {
                return Enums.named(type).cast().apply(version, name).map(type::cast);
            }

            private static <E extends Enum<E>> @NotNull List<Map.Entry<E, String>> enumEntries(
                    int version, @NotNull Class<E> type) {
                return Enums.named(type).entries().apply(version).stream()
                        .map(entry -> Map.entry(type.cast(entry.getKey()), entry.getValue()))
                        .toList();
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

            private static final class Enums {
                private static final @NotNull Map<Class<?>, Numbered<?>> TYPES = new HashMap<>();
                private static final @NotNull Map<Class<?>, Named<?>> NAMED = new HashMap<>();

                static {
                    $enums$
                }

                private Enums() {}

                private static <E extends Enum<E>> void register(
                        @NotNull Class<E> type,
                        @NotNull BiFunction<Integer, E, OptionalInt> integer,
                        @NotNull BiFunction<Integer, Integer, Optional<E>> cast,
                        @NotNull IntFunction<List<E>> values) {
                    TYPES.put(type, new Numbered<>(type, integer, cast, values));
                }

                private static <E extends Enum<E>> void registerNames(
                        @NotNull Class<E> type,
                        @NotNull BiFunction<Integer, E, Optional<String>> name,
                        @NotNull BiFunction<Integer, String, Optional<E>> cast,
                        @NotNull IntFunction<List<Map.Entry<E, String>>> entries) {
                    NAMED.put(type, new Named<>(type, name, cast, entries));
                }

                private static @NotNull Numbered<?> of(@NotNull Class<?> type) {
                    Numbered<?> numbered = TYPES.get(type);
                    if (numbered == null) {
                        throw new IllegalArgumentException(type.getName() + ": is not an enum");
                    }
                    return numbered;
                }

                private static @NotNull Named<?> named(@NotNull Class<?> type) {
                    Named<?> named = NAMED.get(type);
                    if (named == null) {
                        throw new IllegalArgumentException(type.getName() + ": is not a name-coded enum");
                    }
                    return named;
                }
            }

            private record Numbered<E extends Enum<E>>(
                    @NotNull Class<E> type,
                    @NotNull BiFunction<Integer, E, OptionalInt> integer,
                    @NotNull BiFunction<Integer, Integer, Optional<E>> cast,
                    @NotNull IntFunction<List<E>> values) {
                @NotNull OptionalInt enumInteger(int version, @NotNull Object value) {
                    return integer.apply(version, type.cast(value));
                }
            }

            private record Named<E extends Enum<E>>(
                    @NotNull Class<E> type,
                    @NotNull BiFunction<Integer, E, Optional<String>> name,
                    @NotNull BiFunction<Integer, String, Optional<E>> cast,
                    @NotNull IntFunction<List<Map.Entry<E, String>>> entries) {
                @NotNull Optional<String> enumName(int version, @NotNull Object value) {
                    return name.apply(version, type.cast(value));
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
        versions=partial(versions, schema, p),
        registrations=partial(registrations, schema, p, generators),
        enums=partial(enum_registrations, schema, p, enums),
    )


def versions(schema: Schema, p: Printer) -> None:
    for number in schema.versions:
        p.emit(
            """
            public static final class v$number$ {
                public static final int VERSION = $number$;

                private v$number$() {}

                public static byte @NotNull [] encode(@NotNull Packet packet) {
                    return $name$.encode(VERSION, packet);
                }

                public static void encode(@NotNull Packet packet, @NotNull ByteBuf buf) {
                    $name$.encode(VERSION, packet, buf);
                }

                public static <T extends Packet> @NotNull T decode(@NotNull Class<T> type, byte @NotNull [] data) {
                    return $name$.decode(VERSION, type, data);
                }

                public static <T extends Packet> @NotNull T decode(@NotNull Class<T> type, @NotNull ByteBuf buf) {
                    return $name$.decode(VERSION, type, buf);
                }

                public static <E extends Enum<E>> @NotNull OptionalInt enumInteger(@NotNull E value) {
                    return $name$.enumInteger(VERSION, value);
                }

                public static <E extends Enum<E>> @NotNull Optional<E> enumCast(@NotNull Class<E> type, int number) {
                    return $name$.enumCast(VERSION, type, number);
                }

                public static <E extends Enum<E>> boolean enumContains(@NotNull E value) {
                    return $name$.enumInteger(VERSION, value).isPresent();
                }

                public static <E extends Enum<E>> boolean enumContains(@NotNull Class<E> type, int number) {
                    return $name$.enumCast(VERSION, type, number).isPresent();
                }

                public static <E extends Enum<E>> @NotNull List<E> enumValues(@NotNull Class<E> type) {
                    return $name$.enumValues(VERSION, type);
                }

                public static <E extends Enum<E>> int enumCount(@NotNull Class<E> type) {
                    return $name$.enumValues(VERSION, type).size();
                }

                public static <E extends Enum<E>> @NotNull Optional<String> enumName(@NotNull E value) {
                    return $name$.enumName(VERSION, value);
                }

                public static <E extends Enum<E>> @NotNull Optional<E> enumCast(
                        @NotNull Class<E> type, @NotNull String name) {
                    return $name$.enumCast(VERSION, type, name);
                }

                public static <E extends Enum<E>> boolean enumContains(@NotNull Class<E> type, @NotNull String name) {
                    return $name$.enumCast(VERSION, type, name).isPresent();
                }

                public static <E extends Enum<E>> @NotNull List<String> enumNames(@NotNull Class<E> type) {
                    return $name$.enumEntries(VERSION, type).stream().map(Map.Entry::getValue).toList();
                }

                public static <E extends Enum<E>> @NotNull List<Map.Entry<E, String>> enumEntries(
                        @NotNull Class<E> type) {
                    return $name$.enumEntries(VERSION, type);
                }
            }

            """,
            name=names.PROTOCOL,
            number=number,
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


def enum_registrations(schema: Schema, p: Printer, enums: list[EnumModel]) -> None:
    for model in enums:
        numbering = f"{names.internal(schema)}.{names.numbering(schema, model)}"
        p.emit(
            "register($spelled$.class, $numbering$::enumInteger, $numbering$::enumCast, $numbering$::enumValues);",
            spelled=names.qualified(schema, model),
            numbering=numbering,
        )
        if schema.namings(model):
            naming = f"{names.internal(schema)}.{names.naming(schema, model)}"
            p.emit(
                "registerNames($spelled$.class, $naming$::enumName, $naming$::enumCast, $naming$::enumEntries);",
                spelled=names.qualified(schema, model),
                naming=naming,
            )
