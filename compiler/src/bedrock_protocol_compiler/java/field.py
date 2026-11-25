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
    Variant,
)
from bedrock_protocol_compiler.expression import CLASSES, Num, enum_class
from bedrock_protocol_compiler.java import members, names
from bedrock_protocol_compiler.java.expression import Renderer
from bedrock_protocol_compiler.java.members import Members
from bedrock_protocol_compiler.java.union import Union, UnionGenerator, case_name
from bedrock_protocol_compiler.java.value import (
    READS,
    WRITES,
    BitsetValue,
    Body,
    ListValue,
    NamedScalar,
    Reference,
    Scalar,
    Value,
    literal,
)
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import Encoding, EnumModel, Naming, Numbering, Schema, strip


class FieldContext:
    def __init__(
        self,
        schema: Schema,
        encoding: Encoding,
        owner: str,
        where: str,
        field: Field,
        registry: Members,
        inline: bool,
    ) -> None:
        self.schema = schema
        self.encoding = encoding
        self.model = encoding.model
        self.owner = owner
        self.field = field
        self.where = f"{where}.{field.name}"
        self.label = f"{owner}.{names.camel(field.name)}"
        self.members = registry
        self.inline = inline
        self.unions: list[UnionGenerator] = []
        self.numbered = isinstance(field.type, EnumName) and any(
            isinstance(each.type, EnumRef) and other.reached[each.type].model is encoding.reached[field.type].model
            for other in schema.encodings(self.model)
            for each in other.fields
            if each.name == field.name
        )

    def enum_type(self, node: EnumRef | EnumName) -> EnumModel:
        return cast(Numbering | Naming, self.encoding.reached[node]).model

    def value(self, node: Type, label: str) -> Value:
        match node:
            case Primitive(name=name):
                return Scalar(name, node.encoded or name, node.endian, label)
            case AliasRef(alias=alias):
                stored = alias.primitive.name
                return Scalar(stored, node.encoded or stored, None, label)
            case EnumRef():
                enum_type = self.enum_type(node)
                underlying = enum_type.underlying.name
                encoded = node.encoded or ENUM_ENCODINGS[underlying]
                numbering = cast(Numbering, self.encoding.reached[node])
                helper = None
                if not numbering.identity:
                    helper = (
                        f"{names.internal(self.schema)}.{names.numbering(self.schema, enum_type)}",
                        numbering.since,
                    )
                return Scalar(underlying, encoded, node.endian, label, names.qualified(self.schema, enum_type), helper)
            case StructRef():
                child = cast(Encoding, self.encoding.reached[node])
                spelled = names.qualified(self.schema, child.model)
                codec = f"{spelled}.{names.codec(child)}.INSTANCE"
                return Reference(
                    spelled,
                    f"{spelled}.getDefaultInstance()",
                    f"{codec}.decode(buf)",
                    f"{codec}.encode({{}}, buf);",
                    label,
                )
            case EnumName():
                enum_type = self.enum_type(node)
                spelled = names.qualified(self.schema, enum_type)
                if not enum_type.members:
                    raise CompilerError(f"{self.where}: {spelled} has no member to default to")
                naming = cast(Naming, self.encoding.reached[node])
                since = f"{naming.since}, " if len(self.schema.namings(enum_type)) > 1 else ""
                if self.numbered:
                    return NamedScalar(enum_type.underlying.name, label, spelled, since)
                default = f"{spelled}.{(self.schema.default_member(self.model, node) or enum_type.members[0]).name}"
                read = f"{spelled}.decode({since}buf)"
                write = f"{{}}.encode({since}buf);"
                return Reference(spelled, default, read, write, label, number=enum_class(enum_type))
            case BuiltinRef(builtin=builtin):
                codec = names.pascal(names.snake(builtin.name))
                read = f"ByteBufCodec.read{codec}(buf)"
                write = f"ByteBufCodec.write{codec}(buf, {{}});"
                if builtin is UUID:
                    return Reference(builtin.name, "new UUID(0L, 0L)", read, write, label)
                default = f"{builtin.name}.getDefaultInstance()"
                return Reference(builtin.name, default, read, write, label, "{}.copy()")
            case Bitset():
                return BitsetValue(self.schema.width(self.model, node), label)
            case List(element=element, prefix=prefix):
                return ListValue(self.value(element, label), prefix, None, label)
            case Array(element=element, size=size):
                return ListValue(self.value(element, label), None, size, label)
            case Variant(cases=cases):
                wrapper = names.pascal(self.field.name)
                self.unions.append(UnionGenerator(self.union(cases, wrapper, False), self.where))
                codec = f"{wrapper}.{names.codec(self.encoding)}.INSTANCE"
                return Reference(
                    wrapper,
                    f"{wrapper}.getDefaultInstance()",
                    f"{codec}.decode(buf)",
                    f"{codec}.encode({{}}, buf);",
                    self.label,
                )
        kind = type(node).__name__.lower()
        article = "an" if kind[0] in "aeiou" else "a"
        raise CompilerError(f"{self.where}: {article} {kind} inside another type is not supported")

    def union(self, cases: tuple[Type | None, ...], stem: str, inline: bool) -> Union:
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
            built.append((name, self.value(case, f"{stem}.{names.camel(name)}")))
        return Union(self.field.name, built, self.where, inline, self.members)

    def slot(self) -> "Slot":
        node = self.field.type
        label = self.label
        if isinstance(node, Literal) and not self.field.name.strip("_"):
            raise CompilerError(f"{self.where}: a literal needs a name besides underscores")
        slot: Slot
        match node:
            case Literal(value=bool(flag)):
                spelled = literal(flag, CLASSES["bool"])
                slot = LiteralSlot(self.field, label, "bool", spelled, "boolean", spelled)
            case Literal(value=str(text)):
                slot = LiteralSlot(self.field, label, "str", json.dumps(text), "@NotNull String", json.dumps(text))
            case Literal(value=MemberRef(name=name) as member):
                enum_type = self.schema.enum_type(member.enum, self.encoding.since)
                enumerators = self.schema.enumerators(enum_type)
                written = self.schema.number(self.encoding, member)
                encoded = ENUM_ENCODINGS[enum_type.underlying.name]
                enum = names.qualified(self.schema, enum_type)
                canonical = next(
                    (
                        each
                        for each in enum_type.members
                        if name in enumerators and enumerators[each.name] == enumerators[name]
                    ),
                    None,
                )
                if canonical is None:
                    raise CompilerError(f"{self.where}: {enum_type.family.name}.{name} has no constant in {enum}")
                deprecated = canonical.deprecated or any(
                    each.deprecated for each in enum_type.members if each.name == name
                )
                constant = literal(written, CLASSES[encoded])
                slot = LiteralSlot(
                    self.field,
                    label,
                    encoded,
                    constant,
                    f"@NotNull {enum}",
                    f"{enum}.{canonical.name}",
                    deprecated,
                )
            case Optional(element=element):
                slot = OptionalSlot(self.field, label, self.value(element, label))
            case List(element=element, prefix=prefix, count=count):
                slot = ListSlot(self.field, label, ListValue(self.value(element, label), prefix, None, label), count)
            case Array(element=element, size=size):
                slot = ArraySlot(self.field, label, ListValue(self.value(element, label), None, size, label))
            case Map(key=key, value=value):
                slot = MapSlot(self.field, label, self.value(key, label), self.value(value, label))
            case EnumRef():
                slot = EnumSlot(self.field, label, self.value(node, label))
            case EnumName() if self.numbered:
                slot = EnumSlot(self.field, label, self.value(node, label))
            case Variant(cases=cases) if self.inline:
                slot = UnionSlot(self.field, label, self.union(cases, label, True), self.where)
            case _:
                slot = ScalarSlot(self.field, label, self.value(node, label))
        if len(self.unions) > 1:
            raise CompilerError(f"{self.where}: holds more than one union")
        return slot


class Slot:
    term: Num | None = None
    suffix = ""
    bitset = False
    sized = False

    def __init__(self, field: Field, label: str) -> None:
        self.field = field
        self.name = field.name
        self.pascal = names.pascal(field.name)
        self.member = f"{names.camel(field.name)}_"
        self.label = label
        self.copies = field.duplicate

    def declare(self, p: Printer, final: bool) -> None:
        pass

    def construct(self, p: Printer) -> None:
        pass

    def initialize(self, p: Printer) -> None:
        pass

    def adopt(self, p: Printer) -> None:
        pass

    def getters(self, p: Printer, builder: bool) -> None:
        pass

    def setters(self, p: Printer) -> None:
        pass

    def comparisons(self) -> list[str]:
        return []

    def hashes(self) -> list[str]:
        return []

    def types(self) -> list[tuple[str, str]]:
        return []

    def constants(self, p: Printer) -> None:
        pass

    def definitions(self, p: Printer) -> None:
        pass

    def write(self, body: Body, receiver: str) -> None:
        raise NotImplementedError

    def read(self, body: Body, renderer: Renderer) -> None:
        raise NotImplementedError


class StoredSlot(Slot):
    message_type: str

    @property
    def builder_type(self) -> str:
        return self.message_type

    def initial(self) -> str:
        raise NotImplementedError

    def from_message(self, source: str) -> str:
        raise NotImplementedError

    def from_builder(self, source: str) -> str:
        raise NotImplementedError

    def equal(self) -> str:
        raise NotImplementedError

    def hash(self) -> str:
        raise NotImplementedError

    @override
    def declare(self, p: Printer, final: bool) -> None:
        if final:
            p.emit("private final $type$ $member$;", type=self.message_type, member=self.member)
        else:
            p.emit("private $type$ $member$;", type=self.builder_type, member=self.member)

    @override
    def construct(self, p: Printer) -> None:
        p.emit("$member$ = $value$;", member=self.member, value=self.from_builder(f"builder.{self.member}"))

    @override
    def initialize(self, p: Printer) -> None:
        p.emit("$member$ = $value$;", member=self.member, value=self.initial())

    @override
    def adopt(self, p: Printer) -> None:
        p.emit("$member$ = $value$;", member=self.member, value=self.from_message(f"message.{self.member}"))

    @override
    def comparisons(self) -> list[str]:
        return [self.equal()]

    @override
    def hashes(self) -> list[str]:
        return [self.hash()]

    def clear(self, p: Printer) -> None:
        p.emit(
            """
            public @NotNull Builder clear$name$() {
                $member$ = $initial$;
                return this;
            }

            """,
            name=self.pascal,
            member=self.member,
            initial=self.initial(),
        )


def value_setter(p: Printer, value: Value, verb: str, name: str, assign: str) -> None:
    body = Body(p)
    p.emit(
        """
        public @NotNull Builder $verb$$name$Value(int value) {
            $body$
            return this;
        }

        """,
        verb=verb,
        name=name,
        body=lambda: body.line(assign.format(value.adopt(body, "value"))),
    )


class ScalarSlot(StoredSlot):
    def __init__(self, field: Field, label: str, value: Value) -> None:
        super().__init__(field, label)
        self.value = value
        self.message_type = value.java
        if value.number is not None and value.number.kind in ("bool", "int"):
            self.term = value.number
        self.suffix = ".getNumber()" if isinstance(value, Reference) else ""
        self.bitset = isinstance(value, BitsetValue)

    @override
    def initial(self) -> str:
        return self.value.default()

    @override
    def from_message(self, source: str) -> str:
        return self.value.copy(source)

    @override
    def from_builder(self, source: str) -> str:
        return self.value.copy(source)

    @override
    def getters(self, p: Printer, builder: bool) -> None:
        p.emit(
            """
            public $type$ get$name$() {
                return $value$;
            }

            """,
            type=self.value.annotated(),
            name=self.pascal,
            value=self.value.copy(self.member),
        )

    @override
    def setters(self, p: Printer) -> None:
        body = Body(p)
        p.emit(
            """
            public @NotNull Builder set$name$($type$ value) {
                $body$
                return this;
            }

            """,
            name=self.pascal,
            type=self.value.annotated(),
            body=lambda: body.line(f"{self.member} = {self.value.adopt(body, 'value')};"),
        )
        self.clear(p)

    @override
    def equal(self) -> str:
        return self.value.equal(self.member, f"other.{self.member}")

    @override
    def hash(self) -> str:
        return self.value.hash(self.member)

    @override
    def write(self, body: Body, receiver: str) -> None:
        self.value.write(body, f"{receiver}{self.member}")

    @override
    def read(self, body: Body, renderer: Renderer) -> None:
        body.line(f"out.{self.member} = {self.value.read(body)};")


class EnumSlot(ScalarSlot):
    @override
    def getters(self, p: Printer, builder: bool) -> None:
        p.emit(
            """
            public int get$name$Value() {
                return $member$;
            }

            """,
            name=self.pascal,
            member=self.member,
        )
        members.enum_getter(p, str(self.value.enum), self.pascal, self.member)

    @override
    def setters(self, p: Printer) -> None:
        members.enum_setter(p, str(self.value.enum), self.pascal)
        value_setter(p, self.value, "set", self.pascal, f"{self.member} = {{}};")
        self.clear(p)


class OptionalSlot(StoredSlot):
    def __init__(self, field: Field, label: str, element: Value) -> None:
        super().__init__(field, label)
        self.element = element
        self.message_type = element.boxed

    @override
    def initial(self) -> str:
        return "null"

    @override
    def from_message(self, source: str) -> str:
        return self.from_builder(source)

    @override
    def from_builder(self, source: str) -> str:
        if not self.element.mutable:
            return source
        return f"{source} == null ? null : {self.element.copy(source)}"

    @override
    def getters(self, p: Printer, builder: bool) -> None:
        p.emit(
            """
            public boolean has$name$() {
                return $member$ != null;
            }

            """,
            name=self.pascal,
            member=self.member,
        )
        present = f"{self.member} == null ? {self.element.default()} : {self.element.copy(self.member)}"
        if self.element.enum is None:
            p.emit(
                """
                public $type$ get$name$() {
                    return $present$;
                }

                """,
                type=self.element.annotated(),
                name=self.pascal,
                present=present,
            )
            return
        p.emit(
            """
            public int get$name$Value() {
                return $present$;
            }

            """,
            name=self.pascal,
            present=present,
        )
        members.enum_getter(p, self.element.enum, self.pascal, f"get{self.pascal}Value()")

    @override
    def setters(self, p: Printer) -> None:
        if self.element.enum is None:
            body = Body(p)
            p.emit(
                """
                public @NotNull Builder set$name$($type$ value) {
                    $body$
                    return this;
                }

                """,
                name=self.pascal,
                type=self.element.annotated(),
                body=lambda: body.line(f"{self.member} = {self.element.adopt(body, 'value')};"),
            )
        else:
            members.enum_setter(p, self.element.enum, self.pascal)
            value_setter(p, self.element, "set", self.pascal, f"{self.member} = {{}};")
        self.clear(p)

    @override
    def equal(self) -> str:
        return self.element.nullable_equal(self.member, f"other.{self.member}")

    @override
    def hash(self) -> str:
        return self.element.nullable_hash(self.member)

    @override
    def write(self, body: Body, receiver: str) -> None:
        member = f"{receiver}{self.member}"
        body.line(f"buf.writeBoolean({member} != null);")
        body.p.emit(
            """
            if ($member$ != null) {
                $body$
            }
            """,
            member=member,
            body=lambda: self.element.write(body, self.element.unboxed(member)),
        )

    @override
    def read(self, body: Body, renderer: Renderer) -> None:
        body.p.emit(
            """
            if (ByteBufCodec.readBoolean(buf)) {
                $body$
            }
            """,
            body=lambda: body.line(f"out.{self.member} = {self.element.read(body)};"),
        )


class ListSlot(StoredSlot):
    def __init__(self, field: Field, label: str, value: ListValue, count: Expression | None = None) -> None:
        super().__init__(field, label)
        self.value = value
        self.element = value.element
        self.count = count
        self.message_type = value.java
        self.sized = True

    @override
    def initial(self) -> str:
        return "new ArrayList<>()"

    @override
    def from_message(self, source: str) -> str:
        return f"new ArrayList<>({source})"

    @override
    def from_builder(self, source: str) -> str:
        return f"List.copyOf({source})"

    @override
    def getters(self, p: Printer, builder: bool) -> None:
        listed = f"Collections.unmodifiableList({self.member})" if builder else self.member
        enum = self.element.enum
        if enum is None:
            p.emit(
                """
                public @NotNull $type$ get$name$List() {
                    return $listed$;
                }

                """,
                type=self.value.java,
                name=self.pascal,
                listed=listed,
            )
        else:
            p.emit(
                """
                public @NotNull List<$enum$> get$name$List() {
                    List<$enum$> values = new ArrayList<>($member$.size());
                    for (int value : $member$) {
                        $enum$ result = $enum$.forNumber(value);
                        values.add(result == null ? $enum$.UNRECOGNIZED : result);
                    }
                    return Collections.unmodifiableList(values);
                }

                public @NotNull List<Integer> get$name$ValueList() {
                    return $listed$;
                }

                """,
                enum=enum,
                name=self.pascal,
                member=self.member,
                listed=listed,
            )
        p.emit(
            """
            public int get$name$Count() {
                return $member$.size();
            }

            """,
            name=self.pascal,
            member=self.member,
        )
        if enum is None:
            p.emit(
                """
                public $type$ get$name$(int index) {
                    return $member$.get(index);
                }

                """,
                type=self.element.annotated(),
                name=self.pascal,
                member=self.member,
            )
            return
        members.enum_getter(p, enum, self.pascal, f"{self.member}.get(index)", "int index")
        p.emit(
            """
            public int get$name$Value(int index) {
                return $member$.get(index);
            }

            """,
            name=self.pascal,
            member=self.member,
        )

    def element_setter(self, p: Printer, verb: str, index: str, call: str) -> None:
        enum = self.element.enum
        if enum is not None:
            p.emit(
                """
                public @NotNull Builder $verb$$name$($index$@NotNull $enum$ value) {
                    $member$.$call$value.getNumber());
                    return this;
                }

                """,
                verb=verb,
                name=self.pascal,
                index=index,
                enum=enum,
                member=self.member,
                call=call,
            )
            return
        body = Body(p)
        p.emit(
            """
            public @NotNull Builder $verb$$name$($index$$type$ value) {
                $body$
                return this;
            }

            """,
            verb=verb,
            name=self.pascal,
            index=index,
            type=self.element.annotated(),
            body=lambda: body.line(f"{self.member}.{call}{self.element.adopt(body, 'value')});"),
        )

    @override
    def setters(self, p: Printer) -> None:
        self.element_setter(p, "set", "int index, ", "set(index, ")
        self.element_setter(p, "add", "", "add(")
        element = self.element.enum or self.element.boxed
        p.emit(
            """
            public @NotNull Builder addAll$name$(@NotNull Iterable<? extends $element$> values) {
                for ($type$ value : values) {
                    add$name$(value);
                }
                return this;
            }

            """,
            name=self.pascal,
            element=element,
            type=self.element.enum or self.element.java,
        )
        if self.element.enum is not None:
            value_setter(p, self.element, "add", self.pascal, f"{self.member}.add({{}});")
        self.clear(p)

    @override
    def equal(self) -> str:
        return self.value.equal(self.member, f"other.{self.member}")

    @override
    def hash(self) -> str:
        return self.value.hash(self.member)

    @override
    def write(self, body: Body, receiver: str) -> None:
        self.value.write(body, f"{receiver}{self.member}")

    @override
    def read(self, body: Body, renderer: Renderer) -> None:
        count = None if self.count is None else renderer.count(self.count)
        body.line(f"out.{self.member} = {self.value.read_into(body, count)};")


class ArraySlot(ListSlot):
    @override
    def initial(self) -> str:
        return f"new ArrayList<>({self.value.default()})"

    @override
    def setters(self, p: Printer) -> None:
        self.element_setter(p, "set", "int index, ", "set(index, ")
        self.clear(p)


class MapSlot(StoredSlot):
    def __init__(self, field: Field, label: str, key: Value, value: Value) -> None:
        super().__init__(field, label)
        if value.enum is not None or value.mutable:
            raise CompilerError(f"{label}: a {value.java} as a map value is not supported")
        self.key = key
        self.value = value
        self.comparator = key.comparator()
        self.message_type = f"SortedMap<{key.boxed}, {value.boxed}>"
        self.entry = f"{key.boxed}, {value.boxed}"
        self.sized = True

    @property
    @override
    def builder_type(self) -> str:
        return f"TreeMap<{self.entry}>"

    @override
    def initial(self) -> str:
        return f"new TreeMap<>({self.comparator or ''})"

    @override
    def from_message(self, source: str) -> str:
        return f"new TreeMap<>({source})"

    @override
    def from_builder(self, source: str) -> str:
        return f"Collections.unmodifiableSortedMap(new TreeMap<>({source}))"

    @property
    def lookup(self) -> str:
        return (
            "key" if self.key.java in ("boolean", "int", "long", "float", "double") else "Objects.requireNonNull(key)"
        )

    @override
    def getters(self, p: Printer, builder: bool) -> None:
        p.emit(
            """
            public @NotNull Map<$entry$> get$name$Map() {
                return $mapped$;
            }

            public int get$name$Count() {
                return $member$.size();
            }

            public boolean contains$name$($key$ key) {
                return $member$.containsKey($lookup$);
            }

            public $nullable$ get$name$OrDefault($key$ key, $nullable$ defaultValue) {
                $boxed$ value = $member$.get($lookup$);
                return value == null ? defaultValue : value;
            }

            public $value$ get$name$OrThrow($key$ key) {
                $boxed$ value = $member$.get($lookup$);
                if (value == null) {
                    throw new IllegalArgumentException();
                }
                return value;
            }

            """,
            entry=self.entry,
            name=self.pascal,
            mapped=f"Collections.unmodifiableMap({self.member})" if builder else self.member,
            member=self.member,
            key=self.key.annotated(),
            lookup=self.lookup,
            nullable=self.value.annotated(nullable=True),
            boxed=self.value.boxed,
            value=self.value.annotated(),
        )

    @override
    def setters(self, p: Printer) -> None:
        body = Body(p)
        p.emit(
            """
            public @NotNull Builder put$name$($key$ key, $value$ value) {
                $body$
                return this;
            }

            public @NotNull Builder putAll$name$(@NotNull Map<? extends $key_type$, ? extends $value_type$> values) {
                for (Map.Entry<? extends $key_type$, ? extends $value_type$> entry : values.entrySet()) {
                    put$name$(entry.getKey(), entry.getValue());
                }
                return this;
            }

            public @NotNull Builder remove$name$($key$ key) {
                $member$.remove($lookup$);
                return this;
            }

            public @NotNull Builder clear$name$() {
                $member$.clear();
                return this;
            }

            """,
            name=self.pascal,
            key=self.key.annotated(),
            value=self.value.annotated(),
            body=lambda: body.line(
                f"{self.member}.put({self.key.adopt(body, 'key')}, {self.value.adopt(body, 'value')});"
            ),
            key_type=self.key.boxed,
            value_type=self.value.boxed,
            member=self.member,
            lookup=self.lookup,
        )

    @override
    def equal(self) -> str:
        return f"{self.member}.equals(other.{self.member})"

    @override
    def hash(self) -> str:
        return f"{self.member}.hashCode()"

    @override
    def write(self, body: Body, receiver: str) -> None:
        entry = body.fresh("entry")
        body.line(f"ByteBufCodec.writeUnsignedVarInt(buf, {receiver}{self.member}.size());")
        body.p.emit(
            """
            for (Map.Entry<$types$> $entry$ : $member$.entrySet()) {
                $key$
                $value$
            }
            """,
            types=self.entry,
            entry=entry,
            member=f"{receiver}{self.member}",
            key=lambda: self.key.write(body, self.key.unboxed(f"{entry}.getKey()")),
            value=lambda: self.value.write(body, self.value.unboxed(f"{entry}.getValue()")),
        )

    @override
    def read(self, body: Body, renderer: Renderer) -> None:
        total = body.fresh("count")
        entries = body.fresh("map")
        index = body.fresh("i")
        key = body.fresh("key")
        body.line(f"int {total} = ByteBufCodec.toCount(buf, ByteBufCodec.readUvarint32Count(buf));")
        body.line(f"TreeMap<{self.entry}> {entries} = {self.initial()};")
        body.p.emit(
            """
            for (int $index$ = 0; $index$ < $total$; $index$++) {
                try {
                    $key$
                    $entry$
                } catch (DecodeException e) {
                    throw e.prepend($index$);
                }
            }
            """,
            index=index,
            total=total,
            key=lambda: body.line(f"{self.key.java} {key} = {self.key.read(body)};"),
            entry=lambda: body.line(f"{entries}.put({key}, {self.value.read(body)});"),
        )
        body.line(f"out.{self.member} = {entries};")


class LiteralSlot(Slot):
    def __init__(
        self, field: Field, label: str, encoded: str, constant: str, java: str, value: str, deprecated: bool = False
    ) -> None:
        super().__init__(field, label)
        self.encoded = encoded
        self.constant = constant
        self.java = java
        self.value = value
        self.deprecated = deprecated

    @override
    def constants(self, p: Printer) -> None:
        if self.deprecated:
            p.emit("@Deprecated")
        p.emit(
            "public static final $type$ $name$ = $value$;",
            type=self.java,
            name=self.name.lstrip("_").upper(),
            value=self.value,
        )

    @override
    def write(self, body: Body, receiver: str) -> None:
        body.line(WRITES[self.encoded].format(self.constant))

    @override
    def read(self, body: Body, renderer: Renderer) -> None:
        read = READS[self.encoded][0]
        if self.encoded == "bool":
            condition = read if self.constant == "false" else f"!{read}"
        elif self.encoded == "str":
            condition = f"!{read}.equals({self.constant})"
        else:
            condition = f"{read} != {self.constant}"
        body.fail(condition, "unknownValue")


class UnionSlot(Slot):
    def __init__(self, field: Field, label: str, union: Union, where: str) -> None:
        super().__init__(field, label)
        self.union = union
        self.member = union.selector
        self.where = where

    @override
    def declare(self, p: Printer, final: bool) -> None:
        self.union.declare(p, final)

    @override
    def construct(self, p: Printer) -> None:
        self.union.construct(p)

    @override
    def initialize(self, p: Printer) -> None:
        self.union.initialize(p)

    @override
    def adopt(self, p: Printer) -> None:
        self.union.adopt(p)

    @override
    def getters(self, p: Printer, builder: bool) -> None:
        self.union.getters(p)

    @override
    def setters(self, p: Printer) -> None:
        self.union.setters(p)

    @override
    def comparisons(self) -> list[str]:
        return self.union.comparisons()

    @override
    def hashes(self) -> list[str]:
        return self.union.hashes()

    @override
    def types(self) -> list[tuple[str, str]]:
        return [(self.union.kind, self.where)]

    @override
    def definitions(self, p: Printer) -> None:
        self.union.kind_enum(p)

    @override
    def write(self, body: Body, receiver: str) -> None:
        self.union.write(body, receiver)

    @override
    def read(self, body: Body, renderer: Renderer) -> None:
        self.union.read(body)
