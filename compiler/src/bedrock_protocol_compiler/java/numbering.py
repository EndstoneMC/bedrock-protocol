import json
from collections.abc import Callable
from functools import partial

from bedrock_protocol_compiler.descriptor import Literal, MemberRef, Range, Struct
from bedrock_protocol_compiler.java import members, names
from bedrock_protocol_compiler.java.expression import enum_class
from bedrock_protocol_compiler.java.value import literal
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumModel, Numbering, Schema, StructModel


def reached(schema: Schema) -> list[EnumModel]:
    found: dict[EnumModel, None] = {}
    for family in schema.order:
        if not isinstance(family, Struct):
            continue
        for model in schema.models(family):
            if isinstance(model, StructModel):
                for encoding in schema.encodings(model):
                    for each in encoding.reached.values():
                        if isinstance(each, Numbering) and not each.identity:
                            found[each.model] = None
                    for field in encoding.fields:
                        if isinstance(field.type, Literal) and isinstance(field.type.value, MemberRef):
                            numbering = schema.numbering_at(field.type.value.enum, encoding.since)
                            if not numbering.identity:
                                found[numbering.model] = None
    return list(found)


class NumberingGenerator:
    def __init__(self, schema: Schema, model: EnumModel) -> None:
        self.name = names.numbering(schema, model)
        self.family = names.nested(schema, model)
        self.number = enum_class(model)
        self.numberings = schema.numberings(model)
        self.unknown = json.dumps(f"{self.family}: is not a type at protocol ")

    def definition(self, p: Printer) -> None:
        p.emit(
            """
            public final class $name$ {
                private $name$() {}

                public static int toNumber(int protocol, int value) {
                    $to_number$
                }

                public static boolean decodes(int protocol, int number) {
                    $decodes$
                }

                public static int fromNumber(int protocol, int number) {
                    $from_number$
                }
            }
            """,
            name=self.name,
            to_number=lambda: members.ladder(p, self.entries(p, self.to_number), self.unknown),
            decodes=lambda: members.ladder(p, self.entries(p, self.decodes), self.unknown),
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
