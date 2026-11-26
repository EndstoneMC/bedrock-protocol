import json
from collections.abc import Callable
from functools import partial
from itertools import groupby

from bedrock_protocol_compiler.descriptor import CompilerError, Literal, Range, Variant
from bedrock_protocol_compiler.java import members, names
from bedrock_protocol_compiler.java.enum import EnumGenerator
from bedrock_protocol_compiler.java.expression import Renderer
from bedrock_protocol_compiler.java.field import FieldContext, Slot, held
from bedrock_protocol_compiler.java.members import Members
from bedrock_protocol_compiler.java.names import BUILDER, OBJECT
from bedrock_protocol_compiler.java.union import Union, UnionGenerator, case_name
from bedrock_protocol_compiler.java.value import Body
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import (
    Encoding,
    EnumModel,
    Schema,
    SerializationMode,
    StructModel,
    strip,
)

type Built = list[tuple[Slot, list[UnionGenerator]]]
type Served = list[tuple[Range, SerializationMode, str]]
type Span = tuple[int | None, int | None, list[SerializationMode]]

MODES = list(SerializationMode)


def spans(served: Served) -> list[Span]:
    points = sorted({bound for run, _, _ in served for bound in (run.since, run.until) if bound is not None})
    found: list[Span] = []
    for since, until in zip([None, *points], [*points, None], strict=True):
        span = Range(since, until)
        modes = [mode for mode in MODES if any(each is mode and run.overlaps(span) for run, each, _ in served)]
        if found and found[-1][2] == modes:
            found[-1] = (found[-1][0], until, modes)
        else:
            found.append((since, until, modes))
    return found


class MessageGenerator:
    def __init__(
        self,
        schema: Schema,
        model: StructModel,
        enclosing: tuple[str, ...],
        registry: Members,
        exported: set[Encoding],
    ) -> None:
        self.schema = schema
        self.model = model
        self.exported = exported
        self.name = names.declared(schema, model)
        self.qualified = names.qualified(schema, model)
        self.members = registry
        self.top = not enclosing
        self.packet_id = model.family.packet_id
        read = schema.read_at[model]
        form = next(form for form, runs in model.runs.items() if any(run.contains(read) for run in runs))
        self.holder = schema.encoding_at(form, read)
        scope = (*enclosing, self.name)
        self.nested = [
            type_generator(schema, child, scope, registry, exported)
            for child in model.nested
            if schema.owner(child) is model
        ]
        built = self.build(self.holder, registry)
        self.slots = [slot for slot, _ in built if not isinstance(slot.field.type, Literal)]
        self.unions = [union for _, unions in built for union in unions]
        if [slot.name for slot in self.slots] != [slot.name for slot in model.slots]:
            raise CompilerError(f"{self.qualified}: holds its members out of its model's order")
        scratch = Members(Printer())
        kept = {
            slot.name: held(slot, unions)
            for slot, unions in self.build(self.holder, scratch)
            if not isinstance(slot.field.type, Literal)
        }
        self.codecs: list[tuple[Encoding, list[Slot], dict[str, Union]]] = []
        for encoding in sorted(schema.encodings(model), key=lambda each: (each.since, MODES.index(each.mode))):
            if (
                not encoding.fields
                and model.nested
                and self.packet_id is None
                and encoding.excluded is None
                and encoding.reencoded is None
            ):
                continue
            coded = self.build(encoding, scratch)
            for slot, unions in coded:
                if not isinstance(slot.field.type, Literal) and held(slot, unions) != kept[slot.name]:
                    raise CompilerError(
                        f"{self.qualified}.{slot.name}: takes another Java type, setter check or enum form from "
                        f"{encoding.since} than from {self.holder.since}"
                    )
            wrappers = {union.name: union.union for _, unions in coded for union in unions}
            self.codecs.append((encoding, [slot for slot, _ in coded], wrappers))
        types = [(child.name, child.qualified) for child in self.nested]
        types += [(union.name, union.where) for union in self.unions]
        types += [kind for slot in self.slots for kind in slot.types()]
        if self.codecs:
            types.append((BUILDER, f"{self.qualified}.{BUILDER}"))
        codecs = [names.codec(encoding) for encoding, _, _ in self.codecs]
        types += [(codec, names.runtime(schema, names.CODEC)) for codec in codecs]
        members.check_names(self.qualified, types)
        reserved = names.reserved(schema)
        for name, _ in types:
            if name in scope:
                raise CompilerError(f"{self.qualified}.{name}: has the name of a class that encloses it")
            if name in reserved and name != BUILDER:
                raise CompilerError(f"{self.qualified}.{name}: shadows the imported {name}")
        for union in self.unions:
            for name in (BUILDER, union.kind, *codecs):
                if name in (*scope, union.name):
                    raise CompilerError(f"{union.where}.{name}: has the name of a class that encloses it")

    def build(self, encoding: Encoding, registry: Members) -> Built:
        cased = {
            each.name: {
                case_name(strip(case), f"{self.qualified}.{each.name}") for case in each.type.cases if case is not None
            }
            for each in encoding.fields
            if isinstance(each.type, Variant)
        }
        shared = {
            name for name, found in cased.items() if any(found & cased[other] for other in cased if other != name)
        }
        built: Built = []
        for each in encoding.fields:
            inline = each.name not in shared
            context = FieldContext(self.schema, encoding, self.name, self.qualified, each, registry, inline)
            built.append((context.slot(), context.unions))
        return built

    def definition(self, p: Printer) -> None:
        modifiers = "public final class" if self.top else "public static final class"
        if not self.codecs:
            p.emit(
                """
                $modifiers$ $name$ {
                    private $name$() {}

                    $nested$
                }
                """,
                modifiers=modifiers,
                name=self.name,
                nested=lambda: self.definitions(p),
            )
            return
        p.emit(
            """
            $modifiers$ $name$ implements $interface$ {
                $body$
            }
            """,
            modifiers=modifiers,
            name=self.name,
            interface="Message" if self.packet_id is None else "Packet",
            body=lambda: self.body(p),
        )

    def definitions(self, p: Printer) -> None:
        for slot in self.slots:
            slot.definitions(p)
        for union in self.unions:
            union.definition(
                p,
                [
                    (names.codec(each), wrappers[union.name])
                    for each, _, wrappers in self.codecs
                    if union.name in wrappers
                ],
            )
        for child in self.nested:
            child.definition(p)
            p.emit("")

    def body(self, p: Printer) -> None:
        with self.members.scope(self.qualified, self.name):
            if self.packet_id is not None:
                p.emit("public static final int ID = $id$;", id=self.packet_id)
                p.emit("")
            p.emit("private static final $name$ DEFAULT_INSTANCE = new $name$(new Builder());", name=self.name)
            p.emit("")
            for slot in self.slots:
                with self.members.origin(slot.name):
                    slot.declare(p, True)
            p.emit("")
            p.emit("private $name$(Builder builder) {", name=self.name)
            with p.indent():
                for slot in self.slots:
                    slot.construct(p)
            p.emit("}")
            p.emit("")
            members.statics(p, self.name)
            if self.packet_id is not None:
                with self.members.origin(names.runtime(self.schema, "Packet")):
                    p.emit(
                        """
                        @Override
                        public int getPacketId() {
                            return ID;
                        }

                        """
                    )
            for slot in self.slots:
                with self.members.origin(slot.name):
                    slot.getters(p, False)
            self.selector(p)
            with self.members.origin(OBJECT):
                members.equals(p, self.name, [each for slot in self.slots for each in slot.comparisons()])
                members.hash_code(p, [each for slot in self.slots for each in slot.hashes()])
            p.emit("public static final class Builder {")
            with p.indent():
                self.builder(p)
            p.emit("}")
            p.emit("")
            for encoding, slots, _ in self.codecs:
                members.codec(
                    p,
                    self.members,
                    self.qualified,
                    names.codec(encoding),
                    self.name,
                    encoding in self.exported,
                    partial(self.constants, p, slots),
                    partial(self.writes, p, encoding, slots),
                    partial(self.reads, p, encoding, slots),
                )
            self.definitions(p)

    def selector(self, p: Printer) -> None:
        served = sorted(
            (
                (run, mode, names.codec(encoding))
                for encoding, _, _ in self.codecs
                for mode, runs in encoding.served.items()
                for run in runs
            ),
            key=lambda each: (each[0].since or 0, MODES.index(each[1])),
        )
        with self.members.origin(names.runtime(self.schema, names.CODEC)):
            p.emit(
                """
                $modifiers$ @NotNull Codec<$name$> codec(int version) {
                    return codec(version, $mode$.DEFAULT);
                }

                static @NotNull Codec<$name$> codec(int version, @NotNull $mode$ mode) {
                    $selections$
                }

                """,
                modifiers="static" if self.packet_id is None else "public static",
                name=self.name,
                mode=names.MODE,
                selections=lambda: self.selections(p, served),
            )

    def selections(self, p: Printer, served: Served) -> None:
        for run, mode, codec in served:
            p.emit(
                """
                if ($clause$) {
                    return $codec$.INSTANCE;
                }
                """,
                clause=" && ".join(
                    (f"mode == {names.MODE}.{mode.name}", *names.bounded(self.schema, run.since, run.until))
                ),
                codec=codec,
            )
        relative = self.qualified.removeprefix(f"{self.schema.java_package}.")
        for since, until, modes in spans(served):
            if not modes:
                continue
            absent = (
                f"{json.dumps(f'{relative}: no ')} + mode.name().toLowerCase(Locale.ROOT) + "
                f"{json.dumps(' mode at protocol ')} + version + "
                f"{json.dumps('; it has ' + ' and '.join(each.name for each in modes))}"
            )
            p.emit(
                """
                if ($clause$) {
                    throw new IllegalArgumentException($absent$);
                }
                """,
                clause=" && ".join(names.bounded(self.schema, since, until)),
                absent=absent,
            )
        p.emit(
            "throw new IllegalArgumentException($message$ + version);",
            message=json.dumps(f"{relative}: is not a type at protocol "),
        )

    def constants(self, p: Printer, slots: list[Slot]) -> None:
        for slot in slots:
            with self.members.origin(slot.name):
                slot.constants(p)

    def writes(self, p: Printer, encoding: Encoding, slots: list[Slot]) -> None:
        body = Body(p)
        renderer = Renderer(self.schema, encoding, {slot.name: slot for slot in slots}, "value.")
        for when, group in groupby(slots, key=lambda slot: slot.field.when):
            if when is None:
                for slot in group:
                    self.write(body, renderer, slot)
                continue
            p.emit("if ($condition$) {", condition=renderer.predicate(when))
            with p.indent():
                for slot in group:
                    self.write(body, renderer, slot)
            p.emit("}")

    def write(self, body: Body, renderer: Renderer, slot: Slot) -> None:
        self.duplicated(body.p, renderer, slot, lambda: slot.write(body, "value.", renderer))

    def duplicated(self, p: Printer, renderer: Renderer, slot: Slot, each: Callable[[], None]) -> None:
        if slot.copies is None:
            each()
            return
        p.emit(
            """
            for (int copy = 0; copy < $copies$; copy++) {
                $body$
            }
            """,
            copies=renderer.copies(slot.copies),
            body=each,
        )

    def reads(self, p: Printer, encoding: Encoding, slots: list[Slot]) -> None:
        body = Body(p)
        renderer = Renderer(self.schema, encoding, {slot.name: slot for slot in slots}, "out.")
        for when, group in groupby(slots, key=lambda slot: slot.field.when):
            if when is None:
                for slot in group:
                    self.read(body, renderer, slot)
                continue
            p.emit("if ($condition$) {", condition=renderer.predicate(when))
            with p.indent():
                for slot in group:
                    self.read(body, renderer, slot)
            p.emit("}")

    def read(self, body: Body, renderer: Renderer, slot: Slot) -> None:
        body.p.emit(
            """
            try {
                $body$
            } catch (DecodeException e) {
                throw e.prepend($name$).setUnfinishedMessage(out.build());
            }
            """,
            body=lambda: self.duplicated(body.p, renderer, slot, lambda: slot.read(body, renderer)),
            name=json.dumps(slot.name),
        )

    def builder(self, p: Printer) -> None:
        with self.members.scope(f"{self.qualified}.{BUILDER}", BUILDER):
            for slot in self.slots:
                with self.members.origin(slot.name):
                    slot.declare(p, False)
            p.emit("")
            p.emit("private Builder() {")
            with p.indent():
                for slot in self.slots:
                    slot.initialize(p)
            p.emit("}")
            p.emit("")
            p.emit("private Builder($name$ message) {", name=self.name)
            with p.indent():
                for slot in self.slots:
                    slot.adopt(p)
            p.emit("}")
            p.emit("")
            p.emit(
                """
                public @NotNull $name$ build() {
                    return new $name$(this);
                }

                """,
                name=self.name,
            )
            for slot in self.slots:
                with self.members.origin(slot.name):
                    slot.getters(p, True)
                    slot.setters(p)


def type_generator(
    schema: Schema,
    each: StructModel | EnumModel,
    enclosing: tuple[str, ...],
    registry: Members,
    exported: set[Encoding],
) -> MessageGenerator | EnumGenerator:
    if isinstance(each, EnumModel):
        return EnumGenerator(schema, each)
    return MessageGenerator(schema, each, enclosing, registry, exported)
