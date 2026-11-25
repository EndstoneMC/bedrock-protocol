import json

from bedrock_protocol_compiler.descriptor import CompilerError
from bedrock_protocol_compiler.go.value import Body, Reference, Value
from bedrock_protocol_compiler.java.names import pascal
from bedrock_protocol_compiler.printer import Printer


class Case:
    def __init__(self, name: str, value: Value, holder: str) -> None:
        self.name = name
        self.member = pascal(name)
        self.value = value
        self.base = f"{holder}_{self.member}"
        self.wrapper = self.base


class Union:
    """A oneof: the interface its holder's field is typed by and one wrapper struct per case."""

    def __init__(self, holder: str, member: str, cases: list[tuple[str, Value] | None], where: str) -> None:
        self.holder = holder
        self.member = member
        self.interface = f"is{holder}_{member}"
        self.where = where
        self.cases = [None if case is None else Case(case[0], case[1], holder) for case in cases]
        self.optional = None in self.cases
        listed = [case for case in self.cases if case is not None]
        if not listed:
            raise CompilerError(f"{where}: a union needs a case besides None")
        self.first = listed[0]

    def wrap(self, taken: set[str]) -> None:
        for case in self.cases:
            if case is not None and case.base in taken:
                case.wrapper = f"{case.base}_"

    def types(self) -> list[tuple[str, str]]:
        return [(self.interface, self.where)] + [
            (case.wrapper, f"{self.where} case {index}") for index, case in enumerate(self.cases) if case is not None
        ]

    def methods(self) -> list[tuple[str, str]]:
        found = [(f"Get{self.member}", self.where)]
        found += [
            (f"Get{case.member}", f"{self.where} case {index}")
            for index, case in enumerate(self.cases)
            if case is not None
        ]
        return found

    def definition(self, p: Printer) -> None:
        p.emit(
            """
            type $interface$ interface {
                $interface$()
            }

            """,
            interface=self.interface,
        )
        for case in self.cases:
            if case is None:
                continue
            p.emit(
                """
                type $wrapper$ struct {
                    $member$ $type$
                }

                func (*$wrapper$) $interface$() {}

                """,
                wrapper=case.wrapper,
                member=case.member,
                type=case.value.go,
                interface=self.interface,
            )

    def getters(self, p: Printer) -> None:
        p.emit(
            """
            func (x *$holder$) Get$member$() $interface$ {
                if x != nil {
                    return x.$member$
                }
                return nil
            }

            """,
            holder=self.holder,
            member=self.member,
            interface=self.interface,
        )
        for case in self.cases:
            if case is None:
                continue
            p.emit(
                """
                func (x *$holder$) Get$name$() $type$ {
                    if x, ok := x.Get$member$().(*$wrapper$); ok && x != nil {
                        return x.$name$
                    }
                    return $zero$
                }

                """,
                holder=self.holder,
                name=case.member,
                type=case.value.go,
                member=self.member,
                wrapper=case.wrapper,
                zero=case.value.zero,
            )

    def selected(self, body: Body) -> str:
        selected = body.fresh("u")
        body.line(f"{selected} := x.{self.member}")
        if not self.optional:
            body.p.emit(
                """
                if $selected$ == nil {
                    $selected$ = &$wrapper${}
                }
                """,
                selected=selected,
                wrapper=self.first.wrapper,
            )
        return selected

    def write(self, body: Body) -> None:
        selected = self.selected(body)
        body.p.emit(f"switch {selected}.(type) {{")
        for index, case in enumerate(self.cases):
            body.p.emit("case nil:" if case is None else f"case *{case.wrapper}:")
            with body.p.indent():
                body.line(f"w.WriteUvarint32({index})")
                if case is not None:
                    case.value.write(body, f"x.Get{case.member}()")
        body.p.emit("}")

    def read(self, body: Body) -> None:
        body.p.emit("switch r.ReadUvarint32() {")
        for index, case in enumerate(self.cases):
            body.p.emit(f"case {index}:")
            with body.p.indent():
                if case is None:
                    body.line(f"x.{self.member} = nil")
                    continue
                wrapper = body.fresh("c")
                body.line(f"{wrapper} := &{case.wrapper}{{}}")
                body.line(f"{wrapper}.{case.member} = {case.value.read(body)}")
                body.line(f"x.{self.member} = {wrapper}")
        body.p.emit(
            """
            default:
                r.Fail(stream.ErrUnknownValue)
            }
            """
        )

    def case(self, body: Body) -> str:
        selected = self.selected(body)
        arm = body.fresh("a")
        body.line(f"var {arm} any")
        body.p.emit(f"switch {selected}.(type) {{")
        for case in self.cases:
            if case is None:
                continue
            body.p.emit(f"case *{case.wrapper}:")
            with body.p.indent():
                printed = case.value.case(f"x.Get{case.member}()")
                if isinstance(case.value, Reference) and case.value.bound is not None:
                    printed = f"caseClass({json.dumps(case.value.bound)}, {printed})"
                body.line(f"{arm} = {printed}")
        body.p.emit("}")
        return arm
