from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    BuiltinRef,
    CompilerError,
    EnumName,
    EnumRef,
    List,
    Primitive,
    StructRef,
    Type,
)
from bedrock_protocol_compiler.java import members
from bedrock_protocol_compiler.java.members import Members
from bedrock_protocol_compiler.java.names import BUILDER, OBJECT, camel, pascal, snake
from bedrock_protocol_compiler.java.value import Body, Value
from bedrock_protocol_compiler.printer import Printer


def case_name(node: Type, where: str) -> str:
    match node:
        case StructRef(struct=family) | EnumRef(enum=family) | EnumName(enum=family):
            return snake(family.name)
        case BuiltinRef(builtin=builtin):
            return snake(builtin.name)
        case AliasRef(alias=alias):
            return snake(alias.name)
        case Primitive(name=name):
            return name
        case List(element=element):
            return f"{case_name(element, where)}_list"
    raise CompilerError(f"{where}: a union case of this kind has no name")


class Case:
    def __init__(self, name: str, value: Value, member: str, origin: str) -> None:
        self.name = name
        self.constant = name.upper()
        self.pascal = pascal(name)
        self.member = member
        self.origin = origin
        self.value = value


class Union:
    """The members a union adds to the class that holds it: its own wrapper class, or the message that holds it."""

    def __init__(
        self, field: str, cases: list[tuple[str, Value] | None], where: str, inline: bool, registry: Members
    ) -> None:
        self.name = pascal(field)
        self.kind = f"{self.name}Case"
        self.selector = f"{camel(field)}Case_"
        self.unset = f"{field.upper()}_NOT_SET"
        self.origin = field if inline else self.name
        self.members = registry
        self.cases = [
            None
            if case is None
            else Case(
                case[0],
                case[1],
                f"{camel(field)}{pascal(case[0])}_" if inline else f"{camel(case[0])}_",
                f"{field}.{case[0]}" if inline else case[0],
            )
            for case in cases
        ]
        self.constants = [self.unset if case is None else case.constant for case in self.cases]
        spelled = ((constant, f"case {index}") for index, constant in enumerate(self.constants))
        members.check_names(f"{where}.{self.kind}", spelled)
        self.optional = None in self.cases
        self.initial = self.constants[0]
        self.cleared = self.unset if self.optional else self.initial

    def declare(self, p: Printer, final: bool) -> None:
        modifier = "final " if final else ""
        with self.members.origin(self.origin):
            p.emit("private $modifier$$kind$ $selector$;", modifier=modifier, kind=self.kind, selector=self.selector)
        for case in self.cases:
            if case is not None:
                with self.members.origin(case.origin):
                    p.emit(
                        "private $modifier$$type$ $member$;",
                        modifier=modifier,
                        type=case.value.java,
                        member=case.member,
                    )

    def construct(self, p: Printer) -> None:
        p.emit("$selector$ = builder.$selector$;", selector=self.selector)
        for case in self.cases:
            if case is not None:
                p.emit(
                    "$member$ = builder.$selector$ == $kind$.$constant$ ? $copy$ : $default$;",
                    member=case.member,
                    selector=self.selector,
                    kind=self.kind,
                    constant=case.constant,
                    copy=case.value.copy(f"builder.{case.member}"),
                    default=case.value.default(),
                )

    def initialize(self, p: Printer) -> None:
        p.emit("$selector$ = $kind$.$initial$;", selector=self.selector, kind=self.kind, initial=self.initial)
        for case in self.cases:
            if case is not None:
                p.emit("$member$ = $default$;", member=case.member, default=case.value.default())

    def adopt(self, p: Printer) -> None:
        p.emit("$selector$ = message.$selector$;", selector=self.selector)
        for case in self.cases:
            if case is not None:
                p.emit("$member$ = $copy$;", member=case.member, copy=case.value.copy(f"message.{case.member}"))

    def getters(self, p: Printer) -> None:
        with self.members.origin(self.origin):
            p.emit(
                """
                public @NotNull $kind$ get$kind$() {
                    return $selector$;
                }

                """,
                kind=self.kind,
                selector=self.selector,
            )
        for case in self.cases:
            if case is None:
                continue
            value = case.value
            selected = f"{self.selector} == {self.kind}.{case.constant}"
            current = f"{selected} ? {value.copy(case.member)} : {value.default()}"
            with self.members.origin(case.origin):
                p.emit(
                    """
                    public boolean has$name$() {
                        return $selected$;
                    }

                    """,
                    name=case.pascal,
                    selected=selected,
                )
                p.emit(
                    """
                    public $type$ get$name$$suffix$() {
                        return $current$;
                    }

                    """,
                    type="int" if value.enum is not None else value.annotated(),
                    name=case.pascal,
                    suffix="Value" if value.enum is not None else "",
                    current=current,
                )
                if value.enum is not None:
                    members.enum_getter(p, value.enum, case.pascal, f"get{case.pascal}Value()")

    def setters(self, p: Printer) -> None:
        for case in self.cases:
            if case is None:
                continue
            value = case.value
            with self.members.origin(case.origin):
                if value.enum is not None:
                    members.enum_setter(p, value.enum, case.pascal)
                p.emit(
                    "public @NotNull Builder set$name$$suffix$($parameter$ value) {",
                    name=case.pascal,
                    suffix="Value" if value.enum is not None else "",
                    parameter="int" if value.enum is not None else value.annotated(),
                )
                with p.indent():
                    body = Body(p)
                    body.line(f"{case.member} = {value.adopt(body, 'value')};")
                    p.emit(
                        "$selector$ = $kind$.$constant$;",
                        selector=self.selector,
                        kind=self.kind,
                        constant=case.constant,
                    )
                    p.emit("return this;")
                p.emit("}")
                p.emit("")
        reset = None if self.optional else self.cases[0]
        with self.members.origin(self.origin):
            p.emit("public @NotNull Builder clear$name$() {", name=self.name)
            with p.indent():
                p.emit("$selector$ = $kind$.$cleared$;", selector=self.selector, kind=self.kind, cleared=self.cleared)
                if reset is not None:
                    p.emit("$member$ = $default$;", member=reset.member, default=reset.value.default())
                p.emit("return this;")
            p.emit("}")
            p.emit("")

    def write(self, body: Body) -> None:
        body.p.emit(
            """
            ByteBufCodec.writeUnsignedVarInt(buf, $selector$.ordinal());
            switch ($selector$) {
                $cases$
            }
            """,
            selector=self.selector,
            cases=lambda: self.write_cases(body),
        )

    def write_cases(self, body: Body) -> None:
        for constant, case in zip(self.constants, self.cases, strict=True):
            body.p.emit("case $constant$ -> {", constant=constant)
            with body.p.indent():
                if case is not None:
                    case.value.write(body, case.member)
            body.p.emit("}")

    def read(self, body: Body) -> None:
        body.p.emit(
            """
            switch (ByteBufCodec.readUnsignedVarInt(buf)) {
                $cases$
                default -> throw DecodeException.unknownValue(buf.readerIndex());
            }
            """,
            cases=lambda: self.read_cases(body),
        )

    def read_cases(self, body: Body) -> None:
        for index, (constant, case) in enumerate(zip(self.constants, self.cases, strict=True)):
            body.p.emit("case $index$ -> {", index=index)
            with body.p.indent():
                if case is not None:
                    body.line(f"out.{case.member} = {case.value.read(body)};")
                body.p.emit(
                    "out.$selector$ = $kind$.$constant$;", selector=self.selector, kind=self.kind, constant=constant
                )
            body.p.emit("}")

    def comparisons(self) -> list[str]:
        found = [f"{self.selector} == other.{self.selector}"]
        for case in self.cases:
            if case is not None:
                found.append(case.value.equal(case.member, f"other.{case.member}"))
        return found

    def hashes(self) -> list[str]:
        found = [f"Integer.hashCode({self.selector}.ordinal())"]
        for case in self.cases:
            if case is not None:
                found.append(case.value.hash(case.member))
        return found

    def kind_enum(self, p: Printer) -> None:
        p.emit("public enum $kind$ {", kind=self.kind)
        with p.indent():
            for index, constant in enumerate(self.constants, 1):
                p.emit("$constant$$comma$", constant=constant, comma="," if index < len(self.constants) else "")
        p.emit("}")
        p.emit("")


class UnionGenerator:
    """A union wrapped in a message of its own, where its holder cannot hold it as a oneof."""

    def __init__(self, union: Union, where: str, message: str) -> None:
        self.union = union
        self.name = union.name
        self.kind = union.kind
        self.where = where
        self.message = message

    def definition(self, p: Printer) -> None:
        p.emit(
            """
            public static final class $name$ implements Message {
                $body$
            }

            """,
            name=self.name,
            body=lambda: self.body(p),
        )

    def body(self, p: Printer) -> None:
        union = self.union
        with union.members.scope(self.where, self.name):
            p.emit("private static final $name$ DEFAULT_INSTANCE = new $name$(new Builder());", name=self.name)
            p.emit("")
            union.declare(p, True)
            p.emit("")
            p.emit("private $name$(Builder builder) {", name=self.name)
            with p.indent():
                union.construct(p)
            p.emit("}")
            p.emit("")
            members.statics(p, self.name)
            union.getters(p)
            body = Body(p)
            with union.members.origin(self.message):
                p.emit(
                    """
                    @Override
                    public void encode(@NotNull ByteBuf buf) {
                        $body$
                    }

                    """,
                    body=lambda: union.write(body),
                )
            p.emit(
                """
                public static @NotNull $name$ decode(@NotNull ByteBuf buf) {
                    Builder out = new Builder();
                    $read$
                    return out.build();
                }

                """,
                name=self.name,
                read=lambda: union.read(body),
            )
            with union.members.origin(OBJECT):
                members.equals(p, self.name, union.comparisons())
                members.hash_code(p, union.hashes())
            union.kind_enum(p)
            p.emit("public static final class Builder {")
            with p.indent():
                self.builder(p)
            p.emit("}")

    def builder(self, p: Printer) -> None:
        union = self.union
        with union.members.scope(f"{self.where}.{BUILDER}", BUILDER):
            union.declare(p, False)
            p.emit("")
            p.emit("private Builder() {")
            with p.indent():
                union.initialize(p)
            p.emit("}")
            p.emit("")
            p.emit("private Builder($name$ message) {", name=self.name)
            with p.indent():
                union.adopt(p)
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
            union.getters(p)
            union.setters(p)
