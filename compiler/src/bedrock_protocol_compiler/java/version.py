import json

from bedrock_protocol_compiler.java import names
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import Schema


def table(schema: Schema, p: Printer) -> None:
    p.emit(
        """
        public final class $name$ {
            public static final @NotNull List<$name$> SUPPORTED_VERSIONS = List.of(
                    $releases$

            public static final @NotNull $name$ MINIMUM_VERSION = SUPPORTED_VERSIONS.getFirst();

            public static final @NotNull $name$ MAXIMUM_VERSION = SUPPORTED_VERSIONS.getLast();

            private final int protocol;

            private final @NotNull String name;

            private $name$(int protocol, @NotNull String name) {
                this.protocol = protocol;
                this.name = name;
            }

            public int getProtocol() {
                return protocol;
            }

            public @NotNull String getName() {
                return name;
            }

            public static @NotNull Optional<$name$> get(int protocol) {
                if (protocol < $minimum$ || protocol > $maximum$) {
                    return Optional.empty();
                }
                $name$ below = MINIMUM_VERSION;
                for ($name$ version : SUPPORTED_VERSIONS) {
                    if (version.protocol == protocol) {
                        return Optional.of(version);
                    }
                    if (version.protocol < protocol) {
                        below = version;
                    }
                }
                return Optional.of(new $name$(protocol, below.name));
            }
        }
        """,
        name=names.VERSION,
        minimum=schema.versions[0],
        maximum=schema.latest,
        releases=lambda: releases(schema, p),
    )


def releases(schema: Schema, p: Printer) -> None:
    for index, release in enumerate(schema.releases, 1):
        p.emit(
            "new $name$($number$, $first$)$end$",
            name=names.VERSION,
            number=release.number,
            first=json.dumps(release.first),
            end="," if index < len(schema.releases) else ");",
        )
