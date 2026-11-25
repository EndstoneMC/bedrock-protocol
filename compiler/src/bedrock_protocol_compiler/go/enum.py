import json
from collections.abc import Callable
from functools import partial

from bedrock_protocol_compiler.descriptor import Range
from bedrock_protocol_compiler.expression import enum_class
from bedrock_protocol_compiler.go import names
from bedrock_protocol_compiler.go.value import go_of, literal
from bedrock_protocol_compiler.java.members import BARE, branch
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumModel, Naming, Numbering, Schema, qualified

type Entries = list[tuple[list[Range], Callable[[], None]]]


class EnumGenerator:
    def __init__(self, schema: Schema, enum_type: EnumModel, numbered: bool) -> None:
        self.schema = schema
        self.model = enum_type
        self.name = names.declared(schema, enum_type)
        self.helper = names.unexported(self.name)
        self.number = enum_class(enum_type)
        self.underlying = go_of(self.number)
        self.values = schema.enumerators(enum_type)
        self.numbers = {member.name: literal(self.values[member.name], self.number) for member in enum_type.members}
        self.canonical: dict[str, str] = {}
        for member in enum_type.members:
            self.canonical.setdefault(self.numbers[member.name], member.name)
        name_coded = any(form in schema.name_coded for form in enum_type.runs)
        self.namings = schema.namings(enum_type) if name_coded else []
        self.numberings = schema.numberings(enum_type) if numbered else []

    def constant(self, member: str) -> str:
        return f"{self.name}_{member}"

    def identifiers(self) -> list[tuple[str, str]]:
        enum = qualified(self.model.family)
        found = [(self.name, f"the enum {enum}")]
        found += [(f"{self.name}_name", f"the names of {enum}"), (f"{self.name}_value", f"the values of {enum}")]
        found += [(self.constant(member.name), f"{enum}.{member.name}") for member in self.model.members]
        if self.numberings:
            numbering = f"the numbering of {enum}"
            found += [(f"{self.helper}ToNumber", numbering), (f"{self.helper}FromNumber", numbering)]
        if self.namings:
            naming = f"the naming of {enum}"
            found += [(f"{self.helper}Name", naming), (f"{self.helper}FromName", naming)]
        return found

    def definition(self, p: Printer) -> None:
        p.emit("type $name$ $underlying$", name=self.name, underlying=self.underlying)
        p.emit("")
        if self.model.members:
            p.emit("const (")
            with p.indent():
                for member in self.model.members:
                    if member.deprecated:
                        p.emit("// Deprecated: Do not use.")
                    p.emit(
                        "$constant$ $name$ = $number$",
                        constant=self.constant(member.name),
                        name=self.name,
                        number=self.numbers[member.name],
                    )
            p.emit(")")
            p.emit("")
        p.emit(
            """
            var (
                $name$_name = map[$underlying$]string{
                    $names$
                }
                $name$_value = map[string]$underlying${
                    $values$
                }
            )

            func (x $name$) Enum() *$name$ {
                p := new($name$)
                *p = x
                return p
            }

            func (x $name$) String() string {
                if name, ok := $name$_name[$underlying$(x)]; ok {
                    return name
                }
                return $spelled$
            }

            """,
            name=self.name,
            underlying=self.underlying,
            names=lambda: self.name_entries(p),
            values=lambda: self.value_entries(p),
            spelled=("strconv.FormatInt(int64(x), 10)" if self.number.signed else "strconv.FormatUint(uint64(x), 10)"),
        )
        if self.numberings:
            self.numbering(p)
        if self.namings:
            self.naming(p)

    def name_entries(self, p: Printer) -> None:
        for number, member in self.canonical.items():
            p.emit("$number$: $name$,", number=number, name=json.dumps(member))

    def value_entries(self, p: Printer) -> None:
        for member in self.model.members:
            p.emit("$name$: $number$,", name=json.dumps(member.name), number=self.numbers[member.name])

    def numbering(self, p: Printer) -> None:
        p.emit(
            """
            func $helper$ToNumber(protocol int, value $name$) ($underlying$, bool) {
                $encode$
            }

            func $helper$FromNumber(protocol int, number $underlying$) ($name$, bool) {
                $decode$
            }

            """,
            helper=self.helper,
            name=self.name,
            underlying=self.underlying,
            encode=lambda: branch(p, self.entries(p, self.numberings, self.to_number), BARE, "return 0, false"),
            decode=lambda: branch(p, self.entries(p, self.numberings, self.from_number), BARE, "return 0, false"),
        )

    def entries[T: (Numbering, Naming)](self, p: Printer, each: list[T], body: Callable[[Printer, T], None]) -> Entries:
        return [(entry.runs, partial(body, p, entry)) for entry in each]

    def table(self, p: Printer, subject: str, rows: list[tuple[list[str], str]], otherwise: str) -> None:
        rows = [(labels, arm) for labels, arm in rows if labels]
        if rows:
            p.emit("switch $subject$ {", subject=subject)
            for labels, arm in rows:
                p.emit("case $labels$:", labels=", ".join(labels))
                with p.indent():
                    p.emit("return $arm$", arm=arm)
            p.emit("}")
        p.emit("return $otherwise$", otherwise=otherwise)

    def spell(self, value: int) -> str:
        return literal(value, self.number)

    def to_number(self, p: Printer, numbering: Numbering) -> None:
        rows = [([self.spell(each) for each in sorted(numbering.absent)], "0, false")]
        for value, number in sorted(numbering.encoded.items()):
            rows.append(([self.spell(value)], f"{self.spell(number)}, true"))
        self.table(p, "value", rows, f"{self.underlying}(value), true")

    def from_number(self, p: Printer, numbering: Numbering) -> None:
        rows = [([self.spell(each) for each in sorted(numbering.lossy)], "0, false")]
        for number, value in sorted(numbering.decoded.items()):
            rows.append(([self.spell(number)], f"{self.spell(value)}, true"))
        self.table(p, "number", rows, f"{self.name}(number), true")

    def naming(self, p: Printer) -> None:
        p.emit(
            """
            func $helper$Name(protocol int, value $name$) (string, bool) {
                $written$
            }

            func $helper$FromName(protocol int, name string) ($name$, bool) {
                $read$
            }

            """,
            helper=self.helper,
            name=self.name,
            written=lambda: self.ladder_or_table(p, self.written),
            read=lambda: self.ladder_or_table(p, self.read),
        )

    def ladder_or_table(self, p: Printer, body: Callable[[Printer, Naming], None]) -> None:
        if len(self.namings) == 1:
            body(p, self.namings[0])
            return
        absent = '"", false' if body == self.written else "0, false"
        branch(p, self.entries(p, self.namings, body), BARE, f"return {absent}")

    def written(self, p: Printer, naming: Naming) -> None:
        rows = [([self.spell(value)], f"{json.dumps(name)}, true") for value, name in naming.written.items()]
        self.table(p, "value", rows, '"", false')

    def read(self, p: Printer, naming: Naming) -> None:
        rows = [([json.dumps(name)], f"{self.spell(value)}, true") for name, value in naming.read.items()]
        self.table(p, "name", rows, "0, false")
