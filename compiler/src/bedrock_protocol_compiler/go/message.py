from collections.abc import Callable
from itertools import groupby

from bedrock_protocol_compiler.descriptor import CompilerError, Variant
from bedrock_protocol_compiler.go import names
from bedrock_protocol_compiler.go.enum import EnumGenerator
from bedrock_protocol_compiler.go.expression import Renderer
from bedrock_protocol_compiler.go.field import (
    FieldContext,
    ListSlot,
    MapSlot,
    OptionalSlot,
    Slot,
    UnionSlot,
    ValueSlot,
)
from bedrock_protocol_compiler.go.union import Union
from bedrock_protocol_compiler.go.value import Body
from bedrock_protocol_compiler.java.members import check_names
from bedrock_protocol_compiler.java.names import bounded, suffix
from bedrock_protocol_compiler.java.union import case_name
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import (
    Encoding,
    EnumModel,
    Schema,
    SerializationMode,
    StructModel,
    qualified,
    strip,
)

MODES = list(SerializationMode)


def fallible(slot: Slot) -> bool:
    match slot:
        case ValueSlot() | ListSlot():
            return slot.value.fallible
        case OptionalSlot():
            return slot.element.fallible
        case MapSlot():
            return slot.key.fallible or slot.value.fallible
        case UnionSlot():
            return any(case is not None and case.value.fallible for case in slot.union.cases)
    return False


class Codec:
    """One encoding of a model or of a union its fields wrap, with the slots and unions it builds."""

    def __init__(self, encoding: Encoding, slots: list[Slot], wrapped: list[Union]) -> None:
        self.encoding = encoding
        self.name = suffix(encoding)
        self.slots = slots
        self.wrapped = {union.holder: union for union in wrapped}
        self.cased = encoding.excluded is None


class MessageGenerator:
    def __init__(self, schema: Schema, model: StructModel, taken: set[str], numbered: set[EnumModel]) -> None:
        self.schema = schema
        self.model = model
        self.name = names.declared(schema, model)
        self.packet_id = model.family.packet_id
        read = schema.read_at[model]
        form = next(form for form, runs in model.runs.items() if any(run.contains(read) for run in runs))
        holder = schema.encoding_at(form, read)
        self.nested: list[MessageGenerator | EnumGenerator] = [
            type_generator(schema, child, taken, numbered) for child in model.nested if schema.owner(child) is model
        ]
        self.codecs: list[Codec] = []
        for encoding in sorted(schema.encodings(model), key=lambda each: (each.since, MODES.index(each.mode))):
            if not encoding.fields and model.nested and self.packet_id is None and encoding.excluded is None:
                continue
            slots, wrapped = self.build(encoding)
            self.codecs.append(Codec(encoding, slots, wrapped))
        if not self.codecs:
            self.slots: list[Slot] = []
            self.unions: list[Union] = []
            self.wrapped: list[Union] = []
            return
        self.slots, wrapped = self.build(holder)
        self.slots = [slot for slot in self.slots if slot.stored]
        self.unions = [slot.union for slot in self.slots if isinstance(slot, UnionSlot)]
        self.wrapped = wrapped
        if [slot.name for slot in self.slots] != [slot.name for slot in model.slots]:
            raise CompilerError(f"{self.name}: holds its members out of its model's order")
        types = {slot.name: slot.go for slot in self.slots}
        for codec in self.codecs:
            for slot in codec.slots:
                if slot.stored and slot.go != types[slot.name]:
                    raise CompilerError(
                        f"{self.name}.{slot.name}: takes the Go type {slot.go} from {codec.encoding.since} and "
                        f"{types[slot.name]} from {holder.since}"
                    )
        taken.add(self.name)
        taken.update(union.holder for union in self.wrapped)

    def build(self, encoding: Encoding) -> tuple[list[Slot], list[Union]]:
        where = self.name
        cased = {
            each.name: {case_name(strip(case), f"{where}.{each.name}") for case in each.type.cases if case is not None}
            for each in encoding.fields
            if isinstance(each.type, Variant)
        }
        shared = {
            name for name, found in cased.items() if any(found & cased[other] for other in cased if other != name)
        }
        slots: list[Slot] = []
        wrapped: list[Union] = []
        for each in encoding.fields:
            context = FieldContext(self.schema, encoding, self.name, where, each, each.name not in shared)
            slots.append(context.slot())
            wrapped.extend(context.unions)
        return slots, wrapped

    def all_unions(self) -> list[Union]:
        found = [*self.unions, *self.wrapped]
        for codec in self.codecs:
            found += [slot.union for slot in codec.slots if isinstance(slot, UnionSlot)]
            found += list(codec.wrapped.values())
        for child in self.nested:
            if isinstance(child, MessageGenerator):
                found += child.all_unions()
        return found

    def identifiers(self) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        if self.codecs:
            found.append((self.name, f"the message {qualified(self.model.family)}"))
            for union in self.unions:
                found += union.types()
            for union in self.wrapped:
                found.append((union.holder, union.where))
                found += union.types()
        for child in self.nested:
            found += child.identifiers()
        return found

    def check(self) -> None:
        members = [(slot.pascal, slot.name) for slot in self.slots]
        for slot in self.slots:
            if isinstance(slot, UnionSlot):
                members += slot.union.methods()
            else:
                members.append((f"Get{slot.pascal}", slot.name))
        for codec in self.codecs:
            members += [(f"encode{codec.name}", "a codec"), (f"decode{codec.name}", "a codec")]
            if codec.cased:
                members.append((f"case{codec.name}", "a codec"))
        if self.packet_id is not None:
            members += [("PacketId", "Packet"), ("encodeAt", "Packet"), ("decodeAt", "Packet"), ("caseAt", "Packet")]
        check_names(self.name, members)
        for union in self.wrapped:
            methods = [(union.member, union.where), *union.methods()]
            for codec in self.codecs:
                if union.holder in codec.wrapped:
                    methods += [(f"encode{codec.name}", "a codec"), (f"decode{codec.name}", "a codec")]
            check_names(union.holder, methods)
        for child in self.nested:
            if isinstance(child, MessageGenerator):
                child.check()

    def definition(self, p: Printer) -> None:
        if self.codecs:
            self.message(p)
        for union in self.wrapped:
            self.wrapper(p, union)
        for child in self.nested:
            child.definition(p)

    def message(self, p: Printer) -> None:
        p.emit("type $name$ struct {", name=self.name)
        with p.indent():
            for slot in self.slots:
                p.emit("$member$ $type$", member=slot.pascal, type=slot.go)
        p.emit("}")
        p.emit("")
        for slot in self.slots:
            slot.getter(p, self.name)
        for union in self.unions:
            union.definition(p)
        if self.packet_id is not None:
            p.emit(
                """
                func (*$name$) PacketId() int {
                    return $id$
                }

                """,
                name=self.name,
                id=self.packet_id,
            )
            p.emit(
                """
                func (x *$name$) encodeAt(w *stream.Writer, version int) bool {
                    switch {
                    $cases$
                    default:
                        return false
                    }
                    return true
                }

                func (x *$name$) decodeAt(r *stream.Reader, version int) bool {
                    switch {
                    $decodes$
                    default:
                        return false
                    }
                    return true
                }

                """,
                name=self.name,
                cases=lambda: self.selections(p, "x.encode$codec$(w)"),
                decodes=lambda: self.selections(p, "x.decode$codec$(r)"),
            )
        for codec in self.codecs:
            self.codec(p, self.name, codec.name, codec.slots, codec.encoding)

    def selections(self, p: Printer, call: str) -> None:
        for since, until, codec in self.served():
            p.emit("case $clause$:", clause=" && ".join(bounded(self.schema, since, until)))
            with p.indent():
                p.emit(call, codec=codec)

    def served(self) -> list[tuple[int | None, int | None, str]]:
        found = []
        for codec in self.codecs:
            runs = codec.encoding.served.get(SerializationMode.DEFAULT, [])
            found += [(run.since, run.until, codec.name) for run in runs]
        return sorted(found, key=lambda each: each[0] or 0)

    def codec(self, p: Printer, holder: str, name: str, slots: list[Slot], encoding: Encoding) -> None:
        stored = any(slot.stored for slot in slots)
        renderer = Renderer(self.schema, encoding, {slot.name: slot for slot in slots}, holder)
        p.emit("func (x *$holder$) encode$name$(w *stream.Writer) {", holder=holder, name=name)
        with p.indent():
            if stored:
                guard(p, holder)
            self.fields(p, renderer, slots, "w", lambda body, slot: slot.write(body), fallible)
        p.emit("}")
        p.emit("")
        p.emit("func (x *$holder$) decode$name$(r *stream.Reader) {", holder=holder, name=name)
        with p.indent():
            if stored:
                p.emit("*x = $holder${}", holder=holder)
            self.fields(p, renderer, slots, "r", lambda body, slot: slot.read(body, renderer), None)
        p.emit("}")
        p.emit("")

    def fields(
        self,
        p: Printer,
        renderer: Renderer,
        slots: list[Slot],
        stream: str,
        each: Callable[[Body, Slot], None],
        checked: Callable[[Slot], bool] | None,
    ) -> None:
        body = Body(p, stream)
        for when, group in groupby(slots, key=lambda slot: slot.field.when):
            if when is None:
                for slot in group:
                    self.field(body, renderer, slot, each, checked)
                continue
            p.emit("if $condition$ {", condition=renderer.predicate(when))
            with p.indent():
                for slot in group:
                    self.field(body, renderer, slot, each, checked)
            p.emit("}")

    def field(
        self,
        body: Body,
        renderer: Renderer,
        slot: Slot,
        each: Callable[[Body, Slot], None],
        checked: Callable[[Slot], bool] | None,
    ) -> None:
        p = body.p
        if slot.copies is not None:
            p.emit("for c := int32(0); c < $copies$; c++ {", copies=renderer.copies(slot.copies))
            p.prefix += "    "
        each(body, slot)
        if checked is None or checked(slot):
            p.emit(
                """
                if $stream$.Failed() {
                    $stream$.PrependField("$name$")
                    return
                }
                """,
                stream=body.stream,
                name=slot.name,
            )
        if slot.copies is not None:
            p.prefix = p.prefix[:-4]
            p.emit("}")

    def wrapper(self, p: Printer, union: Union) -> None:
        p.emit(
            """
            type $holder$ struct {
                $member$ $interface$
            }

            """,
            holder=union.holder,
            member=union.member,
            interface=union.interface,
        )
        union.getters(p)
        union.definition(p)
        for codec in self.codecs:
            coded = codec.wrapped.get(union.holder)
            if coded is None:
                continue
            p.emit("func (x *$holder$) encode$name$(w *stream.Writer) {", holder=union.holder, name=codec.name)
            with p.indent():
                guard(p, union.holder)
                coded.write(Body(p, "w"))
            p.emit("}")
            p.emit("")
            p.emit("func (x *$holder$) decode$name$(r *stream.Reader) {", holder=union.holder, name=codec.name)
            with p.indent():
                p.emit("*x = $holder${}", holder=union.holder)
                coded.read(Body(p, "r"))
            p.emit("}")
            p.emit("")

    def cases(self, p: Printer) -> None:
        if self.codecs:
            if self.packet_id is not None:
                p.emit(
                    """
                    func (x *$name$) caseAt(version int) any {
                        switch {
                        $cases$
                        }
                        return nil
                    }

                    """,
                    name=self.name,
                    cases=lambda: self.selections(p, "return x.case$codec$()"),
                )
            for codec in self.codecs:
                if not codec.cased:
                    continue
                p.emit("func (x *$holder$) case$name$() any {", holder=self.name, name=codec.name)
                with p.indent():
                    guard(p, self.name)
                    body = Body(p, "o")
                    p.emit("var o caseObject")
                    for slot in codec.slots:
                        slot.case(body)
                    p.emit("return o")
                p.emit("}")
                p.emit("")
                for coded in codec.wrapped.values():
                    p.emit("func (x *$holder$) case$name$() any {", holder=coded.holder, name=codec.name)
                    with p.indent():
                        guard(p, coded.holder)
                        p.emit("return $arm$", arm=coded.case(Body(p, "o")))
                    p.emit("}")
                    p.emit("")
        for child in self.nested:
            if isinstance(child, MessageGenerator):
                child.cases(p)


def guard(p: Printer, holder: str) -> None:
    p.emit(
        """
        if x == nil {
            x = new($holder$)
        }
        """,
        holder=holder,
    )


def type_generator(
    schema: Schema, each: StructModel | EnumModel, taken: set[str], numbered: set[EnumModel]
) -> MessageGenerator | EnumGenerator:
    if isinstance(each, EnumModel):
        taken.add(names.declared(schema, each))
        return EnumGenerator(schema, each, each in numbered)
    return MessageGenerator(schema, each, taken, numbered)
