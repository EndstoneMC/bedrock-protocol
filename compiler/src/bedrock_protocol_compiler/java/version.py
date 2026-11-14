import json

from bedrock_protocol_compiler.java import names
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import Schema


def table(schema: Schema, p: Printer) -> None:
    p.emit(
        """
        public record $name$(
                int number, int snapshot, @NotNull String name, @NotNull String first, @NotNull String last) {
            public static final @NotNull List<Integer> VERSIONS = List.of($versions$);

            public static final int LATEST_VERSION = $latest$;

            public static final @NotNull List<$name$> RELEASES = List.of(
                    $releases$

            public $name$ {
                Objects.requireNonNull(name);
                Objects.requireNonNull(first);
                Objects.requireNonNull(last);
            }

            public static @NotNull Optional<$name$> of(int number) {
                for ($name$ version : RELEASES) {
                    if (version.number == number) {
                        return Optional.of(version);
                    }
                }
                return Optional.empty();
            }

            public static @NotNull Optional<$name$> of(@NotNull String release) {
                int[] wanted = parse(release);
                if (wanted == null) {
                    return Optional.empty();
                }
                for ($name$ version : RELEASES) {
                    if (Arrays.compare(parse(version.first), wanted) <= 0
                            && Arrays.compare(wanted, parse(version.last)) <= 0) {
                        return Optional.of(version);
                    }
                }
                return Optional.empty();
            }

            public @NotNull Packet decodePacket(int packetId, @NotNull ByteBuf buf) {
                return switch (snapshot) {
                    $cases$
                    default -> throw new IllegalStateException($unknown$ + snapshot);
                };
            }

            private static int @Nullable [] parse(@NotNull String text) {
                int[] parts = new int[3];
                int cursor = 0;
                int end = text.length();
                for (int i = 0; i < parts.length; i++) {
                    if (i > 0 && (cursor == end || text.charAt(cursor++) != '.')) {
                        return null;
                    }
                    boolean negative = cursor < end && text.charAt(cursor) == '-';
                    if (negative) {
                        cursor++;
                    }
                    long limit = negative ? -(long) Integer.MIN_VALUE : Integer.MAX_VALUE;
                    int digits = cursor;
                    long value = 0;
                    while (cursor < end && text.charAt(cursor) >= '0' && text.charAt(cursor) <= '9') {
                        value = value * 10 + (text.charAt(cursor) - '0');
                        if (value > limit) {
                            return null;
                        }
                        cursor++;
                    }
                    if (cursor == digits) {
                        return null;
                    }
                    parts[i] = (int) (negative ? -value : value);
                }
                if (cursor != end) {
                    return null;
                }
                return parts;
            }
        }
        """,
        name=names.VERSION,
        versions=", ".join(map(str, schema.versions)),
        latest=schema.latest,
        releases=lambda: releases(schema, p),
        cases=lambda: cases(schema, p),
        unknown=json.dumps(f"{names.VERSION}: no packet registry for snapshot "),
    )


def releases(schema: Schema, p: Printer) -> None:
    for index, release in enumerate(schema.releases, 1):
        p.emit(
            "new $name$($number$, $snapshot$, $release$, $first$, $last$)$end$",
            name=names.VERSION,
            number=release.number,
            snapshot=max(each for each in schema.versions if each <= release.number),
            release=json.dumps(release.name),
            first=json.dumps(release.first),
            last=json.dumps(release.last),
            end="," if index < len(schema.releases) else ");",
        )


def cases(schema: Schema, p: Printer) -> None:
    for version in schema.versions:
        p.emit(
            "case $version$ -> $registry$.$name$.decode(packetId, buf);",
            version=version,
            registry=names.registry(schema, version),
            name=names.REGISTRY,
        )
