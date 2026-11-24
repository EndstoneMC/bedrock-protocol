import json
from functools import partial

from bedrock_protocol_compiler.java import members, names
from bedrock_protocol_compiler.java.enum import EnumGenerator
from bedrock_protocol_compiler.java.value import literal
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumModel, Naming, Schema


class NamingGenerator:
    def __init__(self, schema: Schema, model: EnumModel) -> None:
        self.name = names.naming(schema, model)
        self.qualified = names.qualified(schema, model)
        self.enum = EnumGenerator(schema, model)

    def definition(self, p: Printer) -> None:
        p.emit(
            """
            public final class $name$ {
                private $name$() {}

                public static @NotNull Optional<String> enumName(int protocol, @NotNull $enum$ value) {
                    $names$
                }

                public static @NotNull Optional<$enum$> enumCast(int protocol, @NotNull String name) {
                    $casts$
                }

                public static @NotNull List<Map.Entry<$enum$, String>> enumEntries(int protocol) {
                    $entries$
                }
            }
            """,
            name=self.name,
            enum=self.qualified,
            names=lambda: members.ladder(
                p,
                [(each.runs, partial(self.enum_name, p, each)) for each in self.enum.namings],
                "return Optional.empty();",
            ),
            casts=lambda: members.ladder(
                p,
                [(each.runs, partial(self.enum_cast, p, each)) for each in self.enum.namings],
                "return Optional.empty();",
            ),
            entries=lambda: members.ladder(
                p, [(each.runs, partial(self.enum_entries, p, each)) for each in self.enum.namings], "return List.of();"
            ),
        )

    def enum_name(self, p: Printer, naming: Naming) -> None:
        p.emit(
            """
            return Optional.ofNullable(switch (value) {
                $names$
                default -> null;
            });
            """,
            names=lambda: self.enum.written_cases(p, naming),
        )

    def enum_cast(self, p: Printer, naming: Naming) -> None:
        p.emit(
            """
            return Optional.ofNullable(switch (ByteBufCodec.foldAscii(name)) {
                $constants$
                default -> null;
            });
            """,
            constants=lambda: self.read_cases(p, naming),
        )

    def read_cases(self, p: Printer, naming: Naming) -> None:
        for encoded, value in naming.read.items():
            constant = self.enum.canonical[literal(value, self.enum.number)]
            p.emit(
                "case $encoded$ -> $enum$.$constant$;",
                encoded=json.dumps(encoded),
                enum=self.qualified,
                constant=constant,
            )

    def enum_entries(self, p: Printer, naming: Naming) -> None:
        rows = [
            f"Map.entry({self.qualified}.{member.name}, {json.dumps(naming.written[self.enum.values[member.name]])})"
            for member in self.enum.constants
            if self.enum.values[member.name] in naming.written
        ]
        p.emit("return List.of($rows$);", rows=", ".join(rows))
