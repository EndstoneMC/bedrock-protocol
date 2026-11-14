import json
from collections.abc import Callable
from itertools import groupby

from bedrock_protocol_compiler.descriptor import CompilerError, Variant
from bedrock_protocol_compiler.java import members, names
from bedrock_protocol_compiler.java.enum import EnumGenerator
from bedrock_protocol_compiler.java.expression import Renderer
from bedrock_protocol_compiler.java.field import FieldContext, Slot
from bedrock_protocol_compiler.java.members import Members
from bedrock_protocol_compiler.java.names import BUILDER, OBJECT
from bedrock_protocol_compiler.java.union import UnionGenerator, case_name
from bedrock_protocol_compiler.java.value import Body
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumShape, Schema, Shape, StructShape


class MessageGenerator:
    def __init__(self, schema: Schema, shape: StructShape, enclosing: tuple[str, ...], registry: Members) -> None:
        self.schema = schema
        self.shape = shape
        self.name = shape.family.name
        self.qualified = names.qualified(schema, shape)
        self.members = registry
        self.top = not enclosing
        self.version = schema.versions[0] if shape.ranges[0].since is None else shape.ranges[0].since
        self.packet_id = shape.family.packet_id
        self.serializer = bool(shape.fields) or not shape.nested or self.packet_id is not None
        scope = (*enclosing, self.name)
        self.nested = [
            shape_generator(schema, child, scope, registry)
            for child in shape.nested
            if names.host(schema, child) is shape
        ]
        cased = {
            each.name: {
                case_name(case, f"{self.qualified}.{each.name}") for case in each.type.cases if case is not None
            }
            for each in shape.fields
            if isinstance(each.type, Variant)
        }
        shared = {
            name for name, found in cased.items() if any(found & cased[other] for other in cased if other != name)
        }
        self.slots: list[Slot] = []
        self.unions: list[UnionGenerator] = []
        for each in shape.fields:
            inline = each.name not in shared
            context = FieldContext(schema, self.version, self.name, self.qualified, each, registry, inline)
            self.slots.append(context.slot())
            self.unions += context.unions
        types = [(child.name, child.qualified) for child in self.nested]
        types += [(union.name, union.where) for union in self.unions]
        types += [kind for slot in self.slots for kind in slot.types()]
        if self.serializer:
            types.append((BUILDER, f"{self.qualified}.{BUILDER}"))
        members.check_names(self.qualified, types)
        reserved = names.reserved(schema)
        for name, _ in types:
            if name in scope:
                raise CompilerError(f"{self.qualified}.{name}: has the name of a class that encloses it")
            if name in reserved and name != BUILDER:
                raise CompilerError(f"{self.qualified}.{name}: shadows the imported {name}")
        for union in self.unions:
            for name in (BUILDER, union.kind):
                if name in (*scope, union.name):
                    raise CompilerError(f"{union.where}.{name}: has the name of a class that encloses it")

    def definition(self, p: Printer) -> None:
        modifiers = "public final class" if self.top else "public static final class"
        if not self.serializer:
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
            union.definition(p)
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
                    slot.constants(p)
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
            self.encode(p)
            self.decode(p)
            with self.members.origin(OBJECT):
                members.equals(p, self.name, [each for slot in self.slots for each in slot.comparisons()])
                members.hash_code(p, [each for slot in self.slots for each in slot.hashes()])
            p.emit("public static final class Builder {")
            with p.indent():
                self.builder(p)
            p.emit("}")
            p.emit("")
            self.definitions(p)

    def encode(self, p: Printer) -> None:
        with self.members.origin(names.runtime(self.schema, "Message")):
            p.emit(
                """
                @Override
                public void encode(@NotNull ByteBuf buf) {
                    $body$
                }

                """,
                body=lambda: self.writes(p),
            )

    def writes(self, p: Printer) -> None:
        body = Body(p)
        renderer = Renderer(self.schema, self.version, {slot.name: slot for slot in self.slots}, "")
        for when, group in groupby(self.slots, key=lambda slot: slot.field.when):
            if when is None:
                for slot in group:
                    self.write(body, slot)
                continue
            p.emit("if ($condition$) {", condition=renderer.predicate(when))
            with p.indent():
                for slot in group:
                    self.write(body, slot)
            p.emit("}")

    def write(self, body: Body, slot: Slot) -> None:
        self.bound(body.p, slot, lambda: slot.write(body))

    def bound(self, p: Printer, slot: Slot, each: Callable[[], None]) -> None:
        if slot.bindings == 1:
            each()
            return
        p.emit(
            """
            for (int binding = 0; binding < $bindings$; binding++) {
                $body$
            }
            """,
            bindings=slot.bindings,
            body=each,
        )

    def decode(self, p: Printer) -> None:
        p.emit(
            """
            public static @NotNull $name$ decode(@NotNull ByteBuf buf) {
                Builder out = new Builder();
                $body$
                return out.build();
            }

            """,
            name=self.name,
            body=lambda: self.reads(p),
        )

    def reads(self, p: Printer) -> None:
        body = Body(p)
        renderer = Renderer(self.schema, self.version, {slot.name: slot for slot in self.slots}, "out.")
        for when, group in groupby(self.slots, key=lambda slot: slot.field.when):
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
            body=lambda: self.bound(body.p, slot, lambda: slot.read(body, renderer)),
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


def shape_generator(
    schema: Schema, shape: Shape, enclosing: tuple[str, ...], registry: Members
) -> MessageGenerator | EnumGenerator:
    if isinstance(shape, EnumShape):
        return EnumGenerator(schema, shape)
    return MessageGenerator(schema, shape, enclosing, registry)
