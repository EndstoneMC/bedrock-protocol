import json
from typing import cast, override

from bedrock_protocol_compiler.builder import UUID
from bedrock_protocol_compiler.cpp.field import ENUM_ENCODINGS
from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    Array,
    Bitset,
    BuiltinRef,
    CompilerError,
    EnumName,
    EnumRef,
    Expression,
    Field,
    List,
    Literal,
    Map,
    MemberRef,
    Optional,
    Primitive,
    StructRef,
    Type,
    TypeChoice,
    Variant,
)
from bedrock_protocol_compiler.expression import BOOL, CLASSES, Num, enum_class
from bedrock_protocol_compiler.go import names
from bedrock_protocol_compiler.go.expression import Renderer
from bedrock_protocol_compiler.go.union import Union
from bedrock_protocol_compiler.go.value import (
    BitsetValue,
    Body,
    BuiltinValue,
    ListValue,
    Named,
    Reference,
    Scalar,
    Value,
    literal,
)
from bedrock_protocol_compiler.java.names import pascal, suffix
from bedrock_protocol_compiler.java.union import case_name
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import Encoding, EnumModel, Naming, Numbering, Schema, strip


class FieldContext:
    def __init__(self, schema: Schema, encoding: Encoding, holder: str, where: str, field: Field, inline: bool) -> None:
        self.schema = schema
        self.encoding = encoding
        self.model = encoding.model
        self.holder = holder
        self.field = field
        self.where = f"{where}.{field.name}"
        self.inline = inline
        self.unions: list[Union] = []

    def enum_type(self, node: EnumRef | EnumName) -> EnumModel:
        return cast(Numbering | Naming, self.encoding.reached[node]).model

    def value(self, node: Type) -> Value:
        match node:
            case Primitive(name=name):
                encoded = node.encoded or name
                return Scalar(CLASSES[name], encoded, node.endian, self.where, CLASSES[encoded])
            case AliasRef(alias=alias):
                encoded = node.encoded or alias.primitive.name
                return Scalar(CLASSES[alias.primitive.name], encoded, None, self.where, CLASSES[encoded])
            case EnumRef():
                enum_type = self.enum_type(node)
                underlying = enum_type.underlying.name
                numbering = cast(Numbering, self.encoding.reached[node])
                spelled = names.declared(self.schema, enum_type)
                helper = None if numbering.identity else (names.unexported(spelled), numbering.since)
                return Scalar(
                    enum_class(enum_type),
                    node.encoded or ENUM_ENCODINGS[underlying],
                    node.endian,
                    self.where,
                    BOOL if underlying == "bool" else CLASSES[underlying],
                    spelled,
                    helper,
                )
            case EnumName():
                enum_type = self.enum_type(node)
                spelled = names.declared(self.schema, enum_type)
                if not enum_type.members:
                    raise CompilerError(f"{self.where}: {spelled} has no member to default to")
                naming = cast(Naming, self.encoding.reached[node])
                return Named(spelled, names.unexported(spelled), naming.since, enum_class(enum_type))
            case StructRef():
                child = cast(Encoding, self.encoding.reached[node])
                owned = self.schema.owner(child.model) is not None
                return Reference(
                    names.declared(self.schema, child.model),
                    suffix(child),
                    suffix(full(self.schema, child)),
                    child.model.family.name if owned else self.schema.name(child.model),
                )
            case BuiltinRef(builtin=builtin):
                spelled = f"{names.stem(builtin)}.{builtin.name}"
                return BuiltinValue(names.stem(builtin), builtin.name, f"*new({spelled})", builtin is not UUID)
            case Bitset():
                return BitsetValue(self.schema.width(self.model, node))
            case List(element=element, prefix=prefix, count=None):
                blob = element == Primitive("uint8")
                return ListValue(self.value(element), prefix, None, self.where, blob)
            case Array(element=element, size=size):
                return ListValue(self.value(element), None, size, self.where, False)
            case Variant(cases=cases):
                stem = f"{self.holder}_{pascal(self.field.name)}"
                self.unions.append(self.union(cases, stem, pascal(self.field.name)))
                return Reference(stem, suffix(self.encoding), suffix(full(self.schema, self.encoding)))
        kind = type(node).__name__.lower()
        article = "an" if kind[0] in "aeiou" else "a"
        raise CompilerError(f"{self.where}: {article} {kind} inside another type is not supported")

    def union(self, cases: tuple[Type | None, ...], holder: str, member: str) -> Union:
        built: list[tuple[str, Value] | None] = []
        spelled: dict[str, str] = {}
        for case in cases:
            if case is None:
                built.append(None)
                continue
            name = case_name(strip(case), self.where)
            own = case_name(case, self.where)
            if spelled.setdefault(name, own) != own:
                raise CompilerError(f"{self.where}: union cases {spelled[name]} and {own} are both {name}")
            built.append((name, self.value(case)))
        return Union(holder, member, built, self.where)

    def slot(self, node: Type | None = None) -> "Slot":
        if node is None:
            node = self.field.type
        if isinstance(node, Literal) and not self.field.name.strip("_"):
            raise CompilerError(f"{self.where}: a literal needs a name besides underscores")
        slot: Slot
        match node:
            case Literal(value=bool(flag)):
                slot = LiteralSlot(self.field, "bool", literal(flag, BOOL), literal(flag, BOOL))
            case Literal(value=str(text)):
                slot = LiteralSlot(self.field, "str", json.dumps(text), json.dumps(text))
            case Literal(value=MemberRef() as member):
                enum_type = self.schema.enum_type(member.enum, self.encoding.since)
                underlying = enum_type.underlying.name
                written = self.schema.number(self.encoding, member)
                encoded = ENUM_ENCODINGS[underlying]
                slot = LiteralSlot(
                    self.field, encoded, literal(written, CLASSES[encoded]), literal(written, CLASSES[underlying])
                )
            case Optional(element=element):
                slot = OptionalSlot(self.field, self.value(element))
            case List(element=element, prefix=prefix, count=count):
                blob = element == Primitive("uint8")
                slot = ListSlot(self.field, ListValue(self.value(element), prefix, None, self.where, blob), count)
            case Map(key=key, value=entry):
                slot = MapSlot(self.field, self.value(key), self.value(entry), self.where)
            case Variant(cases=cases) if self.inline:
                slot = UnionSlot(self.field, self.union(cases, self.holder, pascal(self.field.name)))
            case TypeChoice(test=test, when_true=when_true, when_false=when_false):
                slot = ChoiceSlot(self.field, test, self.slot(when_true), self.slot(when_false))
            case EnumName():
                default = self.schema.default_member(self.model, node)
                named = self.value(node)
                values = self.schema.enumerators(self.enum_type(node))
                if default is not None and values[default.name] != 0 and 0 in values.values():
                    raise CompilerError(f"{self.where}: a member at 0 would read as the default {default.name}")
                constant = None if default is None else f"{named.go}_{default.name}"
                slot = ValueSlot(self.field, named, constant)
            case _:
                slot = ValueSlot(self.field, self.value(node))
        if len(self.unions) > 1:
            raise CompilerError(f"{self.where}: holds more than one union")
        return slot


def full(schema: Schema, encoding: Encoding) -> Encoding:
    if encoding.excluded is None and encoding.reencoded is None:
        return encoding
    family = next(iter(encoding.runs))
    return schema.encoding_at(family, encoding.since)


class Slot:
    term: Num | None = None
    bitset = False
    sized = False
    stored = True
    go = ""
    zero = "nil"

    def __init__(self, field: Field) -> None:
        self.field = field
        self.name = field.name
        self.pascal = pascal(field.name)
        self.copies = field.duplicate

    def getter(self, p: Printer, holder: str) -> None:
        p.emit(
            """
            func (x *$holder$) Get$name$() $type$ {
                if x != nil {
                    return x.$name$
                }
                return $zero$
            }

            """,
            holder=holder,
            name=self.pascal,
            type=self.go,
            zero=self.zero,
        )

    def access(self) -> str:
        return f"x.{self.pascal}"

    def operand(self) -> str:
        return self.access()

    def write(self, body: Body, renderer: Renderer) -> None:
        raise NotImplementedError

    def read(self, body: Body, renderer: Renderer) -> None:
        raise NotImplementedError

    def case(self, body: Body) -> None:
        raise NotImplementedError

    def entry(self, body: Body, value: str, literal: bool = False) -> None:
        body.line(f"o = append(o, caseEntry{{{json.dumps(self.name)}, {value}, {str(literal).lower()}}})")


class ValueSlot(Slot):
    def __init__(self, field: Field, value: Value, default: str | None = None) -> None:
        super().__init__(field)
        self.value = value
        self.go = value.go
        self.zero = value.zero
        self.default = default
        if isinstance(value, Scalar | Named) and value.stored.kind in ("int", "bool"):
            self.term = value.stored
        self.bitset = isinstance(value, BitsetValue)

    @override
    def access(self) -> str:
        return f"x.{self.pascal}" if self.default is None else f"x.Get{self.pascal}()"

    @override
    def operand(self) -> str:
        if isinstance(self.value, Scalar | Named):
            return self.value.number(self.access())
        return self.access()

    @override
    def getter(self, p: Printer, holder: str) -> None:
        if self.default is None:
            super().getter(p, holder)
            return
        p.emit(
            """
            func (x *$holder$) Get$name$() $type$ {
                if x != nil && x.$name$ != 0 {
                    return x.$name$
                }
                return $default$
            }

            """,
            holder=holder,
            name=self.pascal,
            type=self.go,
            default=self.default,
        )

    @override
    def write(self, body: Body, renderer: Renderer) -> None:
        self.value.write(body, self.access())

    @override
    def read(self, body: Body, renderer: Renderer) -> None:
        body.line(f"x.{self.pascal} = {self.value.read(body)}")

    @override
    def case(self, body: Body) -> None:
        self.entry(body, self.value.case(self.access()))


class OptionalSlot(Slot):
    def __init__(self, field: Field, element: Value) -> None:
        super().__init__(field)
        self.element = element
        self.held = isinstance(element, Reference)
        self.go = element.go if self.held else f"*{element.go}"

    def present(self, body: Body) -> str:
        body.p.emit("if x.$name$ != nil {", name=self.pascal)
        return f"x.{self.pascal}" if self.held else f"*x.{self.pascal}"

    @override
    def write(self, body: Body, renderer: Renderer) -> None:
        body.line(f"w.WriteBool(x.{self.pascal} != nil)")
        value = self.present(body)
        with body.p.indent():
            self.element.write(body, value)
        body.p.emit("}")

    @override
    def read(self, body: Body, renderer: Renderer) -> None:
        body.p.emit("if r.ReadBool() {")
        with body.p.indent():
            value = self.element.read(body)
            if self.held:
                body.line(f"x.{self.pascal} = {value}")
            else:
                held = body.fresh("h")
                body.line(f"{held} := {value}")
                body.line(f"x.{self.pascal} = &{held}")
        body.p.emit("}")

    @override
    def case(self, body: Body) -> None:
        value = self.present(body)
        with body.p.indent():
            self.entry(body, self.element.case(value))
        body.p.emit("}")


class ListSlot(Slot):
    sized = True

    def __init__(self, field: Field, value: ListValue, count: Expression | None) -> None:
        super().__init__(field)
        self.value = value
        self.count = count
        self.go = value.go
        self.zero = value.zero

    @override
    def write(self, body: Body, renderer: Renderer) -> None:
        self.value.write(body, f"x.{self.pascal}")

    @override
    def read(self, body: Body, renderer: Renderer) -> None:
        count = None if self.count is None else renderer.count(self.count)
        body.line(f"x.{self.pascal} = {self.value.read_into(body, count)}")

    @override
    def case(self, body: Body) -> None:
        self.entry(body, self.value.case(f"x.{self.pascal}"))


class MapSlot(Slot):
    sized = True

    def __init__(self, field: Field, key: Value, value: Value, where: str) -> None:
        super().__init__(field)
        if not isinstance(key, Scalar | Named) or key.go == "[]byte" or key.go == "bool":
            raise CompilerError(f"{where}: a {key.go} is not a map key")
        if isinstance(key, Scalar) and key.enum is not None:
            raise CompilerError(f"{where}: an integer-coded enum is not a map key")
        self.key = key
        self.value = value
        self.go = f"map[{key.go}]{value.go}"

    @override
    def write(self, body: Body, renderer: Renderer) -> None:
        entries = body.fresh("map")
        key = body.fresh("k")
        body.line(f"{entries} := x.{self.pascal}")
        body.line(f"w.WriteUvarint32(uint32(len({entries})))")
        index = body.fresh("i") if self.key.fallible or self.value.fallible else "_"
        body.p.emit(f"for {index}, {key} := range slices.Sorted(maps.Keys({entries})) {{")
        with body.p.indent():
            self.key.write(body, key)
            self.value.write(body, f"{entries}[{key}]")
            if index != "_":
                body.p.emit(
                    """
                    if w.Failed() {
                        w.PrependIndex($index$)
                        break
                    }
                    """,
                    index=index,
                )
        body.p.emit("}")

    @override
    def read(self, body: Body, renderer: Renderer) -> None:
        total = body.fresh("count")
        entries = body.fresh("map")
        index = body.fresh("i")
        body.line(f"{total} := r.ReadUvarint32Count()")
        body.line(f"{entries} := make({self.go}, stream.InitialCapacity({total}))")
        body.p.emit(f"for {index} := 0; {index} < {total}; {index}++ {{")
        with body.p.indent():
            key = body.fresh("k")
            body.line(f"{key} := {self.key.read(body)}")
            body.line(f"{entries}[{key}] = {self.value.read(body)}")
            body.p.emit(
                """
                if r.Failed() {
                    r.PrependIndex($index$)
                    break
                }
                """,
                index=index,
            )
        body.p.emit("}")
        body.line(f"x.{self.pascal} = {entries}")

    @override
    def case(self, body: Body) -> None:
        key = f"func(v {self.key.go}) any {{ return {self.key.case('v')} }}"
        value = f"func(v {self.value.go}) any {{ return {self.value.case('v')} }}"
        self.entry(body, f"caseMap(x.{self.pascal}, {key}, {value})")


class LiteralSlot(Slot):
    stored = False

    def __init__(self, field: Field, encoded: str, constant: str, printed: str) -> None:
        super().__init__(field)
        self.encoded = encoded
        self.method = names.method(encoded)
        self.constant = constant
        self.printed = printed

    @override
    def write(self, body: Body, renderer: Renderer) -> None:
        body.line(f"w.Write{self.method}({self.constant})")

    @override
    def read(self, body: Body, renderer: Renderer) -> None:
        read = f"r.Read{self.method}()"
        if self.encoded == "bool":
            condition = read if self.constant == "false" else f"!{read}"
        else:
            condition = f"{read} != {self.constant}"
        body.fail(condition, "ErrUnknownValue")

    @override
    def case(self, body: Body) -> None:
        self.entry(body, self.printed, True)


class UnionSlot(Slot):
    def __init__(self, field: Field, union: Union) -> None:
        super().__init__(field)
        self.union = union
        self.go = union.interface

    @override
    def getter(self, p: Printer, holder: str) -> None:
        self.union.getters(p)

    @override
    def write(self, body: Body, renderer: Renderer) -> None:
        self.union.write(body)

    @override
    def read(self, body: Body, renderer: Renderer) -> None:
        self.union.read(body)

    @override
    def case(self, body: Body) -> None:
        self.entry(body, self.union.case(body))


class ChoiceSlot(Slot):
    def __init__(self, field: Field, test: Expression, when_true: Slot, when_false: Slot) -> None:
        super().__init__(field)
        self.test = test
        self.when_true = when_true
        self.when_false = when_false
        self.go = when_true.go
        self.zero = when_true.zero
        self.stored = when_true.stored
        self.term = when_true.term
        self.bitset = when_true.bitset
        self.sized = when_true.sized

    @override
    def getter(self, p: Printer, holder: str) -> None:
        self.when_true.getter(p, holder)

    @override
    def access(self) -> str:
        return self.when_true.access()

    @override
    def operand(self) -> str:
        return self.when_true.operand()

    @override
    def write(self, body: Body, renderer: Renderer) -> None:
        branch: Slot = self
        keyword = "if"
        while isinstance(branch, ChoiceSlot):
            body.p.emit("$keyword$ $condition$ {", keyword=keyword, condition=renderer.predicate(branch.test))
            with body.p.indent():
                branch.when_true.write(body, renderer)
            keyword = "} else if"
            branch = branch.when_false
        body.p.emit("} else {")
        with body.p.indent():
            branch.write(body, renderer)
        body.p.emit("}")

    @override
    def read(self, body: Body, renderer: Renderer) -> None:
        branch: Slot = self
        keyword = "if"
        while isinstance(branch, ChoiceSlot):
            body.p.emit("$keyword$ $condition$ {", keyword=keyword, condition=renderer.predicate(branch.test))
            with body.p.indent():
                branch.when_true.read(body, renderer)
            keyword = "} else if"
            branch = branch.when_false
        body.p.emit("} else {")
        with body.p.indent():
            branch.read(body, renderer)
        body.p.emit("}")

    @override
    def case(self, body: Body) -> None:
        self.when_true.case(body)
