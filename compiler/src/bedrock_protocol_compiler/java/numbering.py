import json
from collections.abc import Callable
from functools import partial

from bedrock_protocol_compiler.descriptor import Enum, Range
from bedrock_protocol_compiler.java import members, names
from bedrock_protocol_compiler.java.expression import enum_class
from bedrock_protocol_compiler.java.value import literal
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumModel, Numbering, Schema


def enums(schema: Schema) -> list[EnumModel]:
    return list(
        dict.fromkeys(
            model for family in schema.order if isinstance(family, Enum) for model in schema.enum_types(family)
        )
    )


class NumberingGenerator:
    def __init__(self, schema: Schema, model: EnumModel) -> None:
        self.name = names.numbering(schema, model)
        self.family = names.nested(schema, model)
        self.qualified = names.qualified(schema, model)
        self.number = enum_class(model)
        self.numberings = schema.numberings(model)
        message = json.dumps(f"{self.family}: is not a type at protocol ")
        self.unknown = f"throw new IllegalArgumentException({message} + protocol);"

    def definition(self, p: Printer) -> None:
        p.emit(
            """
            public final class $name$ {
                private $name$() {}

                public static int toNumber(int protocol, int value) {
                    $to_number$
                }

                public static boolean encodes(int protocol, int value) {
                    $encodes$
                }

                public static boolean decodes(int protocol, int number) {
                    $decodes$
                }

                public static int fromNumber(int protocol, int number) {
                    $from_number$
                }

                public static @NotNull OptionalInt enumInteger(int protocol, @NotNull $enum$ value) {
                    return encodes(protocol, value.getNumber())
                            ? OptionalInt.of(toNumber(protocol, value.getNumber()))
                            : OptionalInt.empty();
                }

                public static @NotNull Optional<$enum$> enumCast(int protocol, int number) {
                    if (!decodes(protocol, number)) {
                        return Optional.empty();
                    }
                    $enum$ value = $enum$.forNumber(fromNumber(protocol, number));
                    return Optional.of(value == null ? $enum$.UNRECOGNIZED : value);
                }

                public static @NotNull List<$enum$> enumValues(int protocol) {
                    return Arrays.stream($enum$.values())
                            .filter(value -> value != $enum$.UNRECOGNIZED && encodes(protocol, value.getNumber()))
                            .toList();
                }
            }
            """,
            name=self.name,
            enum=self.qualified,
            to_number=lambda: members.ladder(p, self.entries(p, self.to_number), self.unknown),
            encodes=lambda: members.ladder(p, self.entries(p, self.encodes), "return false;"),
            decodes=lambda: members.ladder(p, self.entries(p, self.decodes), "return false;"),
            from_number=lambda: members.ladder(p, self.entries(p, self.from_number), self.unknown),
        )

    def entries(
        self, p: Printer, method: Callable[[Printer, Numbering], None]
    ) -> list[tuple[list[Range], Callable[[], None]]]:
        return [(each.runs, partial(method, p, each)) for each in self.numberings]

    def to_number(self, p: Printer, numbering: Numbering) -> None:
        rows = [(sorted(numbering.absent), self.refuse("value", "has no number"))]
        rows += [([value], self.spell(number)) for value, number in sorted(numbering.encoded.items())]
        self.table(p, "value", rows, "value")

    def encodes(self, p: Printer, numbering: Numbering) -> None:
        self.table(p, "value", [(sorted(numbering.absent), "false")], "true")

    def decodes(self, p: Printer, numbering: Numbering) -> None:
        self.table(p, "number", [(sorted(numbering.lossy), "false")], "true")

    def from_number(self, p: Printer, numbering: Numbering) -> None:
        rows = [(sorted(numbering.lossy), self.refuse("number", "has no value"))]
        rows += [([number], self.spell(value)) for number, value in sorted(numbering.decoded.items())]
        self.table(p, "number", rows, "number")

    def refuse(self, subject: str, reason: str) -> str:
        message = f'"{self.family}: " + {subject} + " {reason} at protocol " + protocol'
        return f"throw new IllegalArgumentException({message})"

    def spell(self, value: int) -> str:
        return literal(value, self.number)

    def table(self, p: Printer, subject: str, rows: list[tuple[list[int], str]], default: str) -> None:
        rows = [(labels, arm) for labels, arm in rows if labels]
        if not rows:
            p.emit("return $default$;", default=default)
            return
        p.emit(
            """
            return switch ($subject$) {
                $cases$
                default -> $default$;
            };
            """,
            subject=subject,
            cases=lambda: self.cases(p, rows),
            default=default,
        )

    def cases(self, p: Printer, rows: list[tuple[list[int], str]]) -> None:
        for labels, arm in rows:
            p.emit("case $labels$ -> $arm$;", labels=", ".join(self.spell(each) for each in labels), arm=arm)
