import json
from collections.abc import Callable
from typing import Protocol

from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.expression import render_count
from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    Array,
    Bitset,
    BuiltinRef,
    Enum,
    EnumName,
    EnumRef,
    List,
    Literal,
    Map,
    MemberRef,
    Optional,
    Primitive,
    Struct,
    StructRef,
    Type,
    Variant,
)
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import Encoding, Schema, StructModel

ENUM_ENCODINGS = {
    "bool": "bool",
    "int8": "int8",
    "uint8": "uint8",
    "int16": "varint32",
    "uint16": "uvarint32",
    "int32": "varint32",
    "uint32": "uvarint32",
}


def primitive_includes(node: Primitive) -> set[str]:
    if node.name == "str":
        return {"<string>"}
    if node.name == "bytes":
        return {"<cstddef>", "<vector>"}
    return {"<cstdint>"} if names.PRIMITIVES[node.name].startswith("std::") else set()


def write_loop(p: Printer, depth: int, indexed: bool, range_: str, *bodies: Callable[[], None]) -> None:
    index = f"std::size_t i{depth} = 0; " if indexed else ""
    p.emit("for ($index$$range$) {", index=index, range=range_)
    with p.indent():
        for body in bodies:
            body()
        if indexed:
            p.emit("++i$depth$;", depth=depth)
    p.emit("}")


def cpp_type(schema: Schema, model: StructModel, node: Type) -> str:
    match node:
        case Primitive(name=name):
            return names.PRIMITIVES[name]
        case AliasRef(alias=alias):
            return names.qualified(schema, alias)
        case BuiltinRef(builtin=builtin):
            return names.qualified(schema, builtin)
        case EnumRef() | StructRef() | EnumName():
            return names.qualified(schema, schema.target(model, node))
        case Bitset():
            return f"std::bitset<{schema.width(model, node)}>"
        case Optional(element=element):
            return f"std::optional<{cpp_type(schema, model, element)}>"
        case List(element=element):
            return f"std::vector<{cpp_type(schema, model, element)}>"
        case Array(element=element, size=size):
            return f"std::array<{cpp_type(schema, model, element)}, {size}>"
        case Map(key=key, value=value):
            return f"std::map<{cpp_type(schema, model, key)}, {cpp_type(schema, model, value)}>"
        case Variant(cases=cases):
            spelled = ("std::monostate" if case is None else cpp_type(schema, model, case) for case in cases)
            return f"std::variant<{', '.join(spelled)}>"
    raise AssertionError(node)


class FieldGenerator(Protocol):
    def includes(self) -> set[str]: ...

    def fallible(self) -> bool: ...

    def write(self, p: Printer, value: str) -> None: ...

    def read(self, p: Printer, target: str) -> None: ...


class ScalarField:
    def __init__(self, where: str, spelled: str, stored: str, encoded: str, endian: str | None) -> None:
        self.where = where
        self.spelled = spelled
        self.stored = stored
        self.encoded = encoded
        self.endian = endian

    def fallible(self) -> bool:
        return False

    def write(self, p: Printer, value: str) -> None:
        p.emit(names.write(self.encoded, self.endian, value))

    def read(self, p: Printer, target: str) -> None:
        p.emit("{")
        with p.indent():
            p.emit("auto v = $call$;", call=names.read(self.encoded, self.endian))
            p.emit("if (!v) $fail$", fail=names.fail("v.error()", self.where))
            if self.encoded in ("str", "bytes"):
                p.emit("$target$ = std::move(*v);", target=target)
            elif self.spelled == names.PRIMITIVES[self.encoded]:
                p.emit("$target$ = *v;", target=target)
            else:
                p.emit("$target$ = static_cast<$type$>(*v);", target=target, type=self.spelled)
            if names.PRIMITIVES[self.stored] != names.PRIMITIVES[self.encoded]:
                p.emit(
                    "if (static_cast<$encoded$>($target$) != *v) $fail$",
                    encoded=names.PRIMITIVES[self.encoded],
                    target=target,
                    fail=names.fail(names.OUT_OF_RANGE, self.where),
                )
        p.emit("}")


class PrimitiveField(ScalarField):
    def __init__(self, node: Primitive, where: str) -> None:
        super().__init__(where, names.PRIMITIVES[node.name], node.name, node.encoded or node.name, node.endian)
        self.node = node

    def includes(self) -> set[str]:
        return primitive_includes(self.node)


class AliasField(ScalarField):
    def __init__(self, schema: Schema, node: AliasRef, where: str) -> None:
        stored = node.alias.primitive.name
        super().__init__(where, names.qualified(schema, node.alias), stored, node.encoded or stored, None)
        self.node = node

    def includes(self) -> set[str]:
        return {names.header(self.node.alias)}


class EnumField(ScalarField):
    def __init__(self, schema: Schema, node: EnumRef, encoding: Encoding, where: str) -> None:
        enum_type = schema.enum_type(node.enum, encoding.since)
        stored = enum_type.underlying.name
        super().__init__(
            where, names.qualified(schema, enum_type), stored, node.encoded or ENUM_ENCODINGS[stored], node.endian
        )
        self.node = node

    def includes(self) -> set[str]:
        return {names.header(self.node.enum)}


class SerializerField:
    def __init__(self, where: str, implementation: str) -> None:
        self.where = where
        self.implementation = implementation

    def fallible(self) -> bool:
        return True

    def write(self, p: Printer, value: str) -> None:
        p.emit(
            """
            {
                auto r = $implementation$::serialize(stream, $value$);
                if (!r) $fail$
            }
            """,
            implementation=self.implementation,
            value=value,
            fail=names.fail("r.error()", self.where),
        )

    def read(self, p: Printer, target: str) -> None:
        p.emit(
            """
            {
                auto v = $implementation$::deserialize(stream);
                if (!v) $fail$
                $target$ = std::move(*v);
            }
            """,
            implementation=self.implementation,
            fail=names.fail("v.error()", self.where),
            target=target,
        )


class ReferenceField(SerializerField):
    def __init__(self, schema: Schema, node: StructRef | EnumName, encoding: Encoding, where: str) -> None:
        self.family: Struct | Enum
        if isinstance(node, StructRef):
            self.family = node.struct
            child = encoding.reached[node]
            assert isinstance(child, Encoding)
            spelled = names.qualified(schema, child.model)
            implementation = names.serializer(spelled, *schema.call(encoding, node))
        else:
            self.family = node.enum
            enum_type = schema.enum_type(node.enum, encoding.since)
            spelled = names.qualified(schema, enum_type)
            implementation = names.serializer(spelled, names.since(schema, enum_type))
        super().__init__(where, implementation)

    def includes(self) -> set[str]:
        return {names.header(self.family)}


class BuiltinField(SerializerField):
    def __init__(self, schema: Schema, node: BuiltinRef, encoding: Encoding, where: str) -> None:
        spelled = names.qualified(schema, node.builtin)
        super().__init__(where, names.serializer(spelled, encoding.since))
        self.node = node

    def includes(self) -> set[str]:
        return {names.header(self.node.builtin)}


class BuiltinTextField:
    def __init__(self, schema: Schema, node: BuiltinRef, where: str) -> None:
        self.node = node
        self.where = where
        self.spelled = names.qualified(schema, node.builtin)

    def fallible(self) -> bool:
        return False

    def includes(self) -> set[str]:
        return {"<string>", names.header(self.node.builtin)}

    def write(self, p: Printer, value: str) -> None:
        p.emit(names.write("str", None, f"{value}.asString()"))

    def read(self, p: Printer, target: str) -> None:
        p.emit(
            """
            {
                auto v = $call$;
                if (!v) $fail$
                auto parsed = $type$::fromString(*v);
                if (!parsed) $unknown$
                $target$ = *parsed;
            }
            """,
            call=names.read("str", None),
            fail=names.fail("v.error()", self.where),
            type=self.spelled,
            unknown=names.fail(names.UNKNOWN_VALUE, self.where),
            target=target,
        )


class BitsetField(SerializerField):
    def __init__(self, schema: Schema, node: Bitset, encoding: Encoding, where: str) -> None:
        spelled = f"std::bitset<{schema.width(encoding.model, node)}>"
        super().__init__(where, names.serializer(spelled, encoding.since))
        self.node = node

    def includes(self) -> set[str]:
        return {"<bitset>", names.runtime("detail/bitset"), names.header(self.node.width.enum)}


class LiteralField:
    def __init__(self, schema: Schema, node: Literal, encoding: Encoding, where: str) -> None:
        self.node = node
        self.where = where
        match node.value:
            case bool(flag):
                self.encoded = "bool"
                self.constant = "true" if flag else "false"
                self.expected = self.constant
            case str(text):
                self.encoded = "str"
                self.constant = json.dumps(text)
                self.expected = self.constant
            case MemberRef() as member:
                enum_type = schema.enum_type(member.enum, encoding.since)
                self.encoded = ENUM_ENCODINGS[enum_type.underlying.name]
                self.constant = names.enumerator(schema, member, encoding)
                self.expected = f"static_cast<{names.PRIMITIVES[self.encoded]}>({self.constant})"

    def fallible(self) -> bool:
        return False

    def includes(self) -> set[str]:
        if isinstance(self.node.value, MemberRef):
            return {names.header(self.node.value.enum)}
        return set()

    def write(self, p: Printer, value: str) -> None:
        p.emit(names.write(self.encoded, None, self.constant))

    def read(self, p: Printer, target: str) -> None:
        p.emit(
            """
            {
                auto v = $call$;
                if (!v) $fail$
                if (*v != $expected$) $mismatch$
            }
            """,
            call=names.read(self.encoded, None),
            fail=names.fail("v.error()", self.where),
            expected=self.expected,
            mismatch=names.fail(names.UNKNOWN_VALUE, self.where),
        )


class OptionalField:
    def __init__(self, schema: Schema, node: Optional, encoding: Encoding, where: str, depth: int) -> None:
        self.element = make_field_generator(schema, node.element, encoding, where, depth)
        self.where = where
        self.depth = depth

    def fallible(self) -> bool:
        return self.element.fallible()

    def includes(self) -> set[str]:
        return {"<optional>"} | self.element.includes()

    def write(self, p: Printer, value: str) -> None:
        p.emit(names.write("bool", None, f"{value}.has_value()"))
        p.emit(
            """
            if ($value$.has_value()) {
                $body$
            }
            """,
            value=value,
            body=lambda: self.element.write(p, f"(*{value})"),
        )

    def read(self, p: Printer, target: str) -> None:
        p.emit(
            """
            {
                auto present$depth$ = $call$;
                if (!present$depth$) $fail$
                if (*present$depth$) {
                    $target$.emplace();
                    $body$
                }
            }
            """,
            depth=self.depth,
            call=names.read("bool", None),
            fail=names.fail(f"present{self.depth}.error()", self.where),
            target=target,
            body=lambda: self.element.read(p, f"(*{target})"),
        )


class ListField:
    def __init__(self, schema: Schema, node: List, encoding: Encoding, where: str, depth: int) -> None:
        self.schema = schema
        self.node = node
        self.encoding = encoding
        self.where = where
        self.depth = depth
        self.element = make_field_generator(schema, node.element, encoding, f"{where}, i{depth}", depth + 1)

    def fallible(self) -> bool:
        return self.element.fallible()

    def includes(self) -> set[str]:
        return {"<vector>"} | self.element.includes()

    def write(self, p: Printer, value: str) -> None:
        if self.node.prefix is not None:
            p.emit(names.write(self.node.prefix.name, self.node.prefix.endian, f"{value}.size()"))
        write_loop(
            p,
            self.depth,
            self.element.fallible(),
            f"const auto &e{self.depth} : {value}",
            lambda: self.element.write(p, f"e{self.depth}"),
        )

    def read(self, p: Printer, target: str) -> None:
        signed = False
        if self.node.prefix is not None:
            count = names.read(self.node.prefix.name, self.node.prefix.endian)
            signed = names.PRIMITIVES[self.node.prefix.name].startswith("std::int")
        else:
            assert self.node.count is not None
            count = render_count(self.schema, self.encoding, self.node.count, "out")
        p.emit("{")
        with p.indent():
            p.emit("auto count$depth$ = $count$;", depth=self.depth, count=count)
            p.emit(
                "if (!count$depth$) $fail$",
                depth=self.depth,
                fail=names.fail(f"count{self.depth}.error()", self.where),
            )
            if signed:
                p.emit(
                    "if (*count$depth$ < 0) $fail$",
                    depth=self.depth,
                    fail=names.fail(names.OUT_OF_RANGE, self.where),
                )
            p.emit(
                """
                $target$.reserve(static_cast<std::size_t>(*count$depth$));
                for (std::size_t i$depth$ = 0; i$depth$ < static_cast<std::size_t>(*count$depth$); ++i$depth$) {
                    $target$.emplace_back();
                    $body$
                }
                """,
                depth=self.depth,
                target=target,
                body=lambda: self.element.read(p, f"{target}.back()"),
            )
        p.emit("}")


class ArrayField:
    def __init__(self, schema: Schema, node: Array, encoding: Encoding, where: str, depth: int) -> None:
        self.node = node
        self.where = where
        self.depth = depth
        self.element = make_field_generator(schema, node.element, encoding, f"{where}, i{depth}", depth + 1)

    def fallible(self) -> bool:
        return self.element.fallible()

    def includes(self) -> set[str]:
        return {"<array>"} | self.element.includes()

    def write(self, p: Printer, value: str) -> None:
        write_loop(
            p,
            self.depth,
            self.element.fallible(),
            f"const auto &e{self.depth} : {value}",
            lambda: self.element.write(p, f"e{self.depth}"),
        )

    def read(self, p: Printer, target: str) -> None:
        p.emit(
            """
            {
                for (std::size_t i$depth$ = 0; i$depth$ < $size$; ++i$depth$) {
                    $body$
                }
            }
            """,
            depth=self.depth,
            size=self.node.size,
            body=lambda: self.element.read(p, f"{target}[i{self.depth}]"),
        )


class MapField:
    def __init__(self, schema: Schema, node: Map, encoding: Encoding, where: str, depth: int) -> None:
        self.where = where
        self.depth = depth
        self.container = cpp_type(schema, encoding.model, node)
        self.key = make_field_generator(schema, node.key, encoding, f"{where}, i{depth}", depth + 1)
        self.value = make_field_generator(schema, node.value, encoding, f"{where}, i{depth}", depth + 1)

    def fallible(self) -> bool:
        return self.key.fallible() or self.value.fallible()

    def includes(self) -> set[str]:
        return {"<map>"} | self.key.includes() | self.value.includes()

    def write(self, p: Printer, value: str) -> None:
        p.emit(names.write("uvarint32", None, f"{value}.size()"))
        write_loop(
            p,
            self.depth,
            self.fallible(),
            f"const auto &[k{self.depth}, v{self.depth}] : {value}",
            lambda: self.key.write(p, f"k{self.depth}"),
            lambda: self.value.write(p, f"v{self.depth}"),
        )

    def read(self, p: Printer, target: str) -> None:
        p.emit(
            """
            {
                auto count$depth$ = $count$;
                if (!count$depth$) $fail$
                for (std::size_t i$depth$ = 0; i$depth$ < static_cast<std::size_t>(*count$depth$); ++i$depth$) {
                    $container$::key_type key$depth${};
                    $container$::mapped_type element$depth${};
                    $key$
                    $element$
                    $target$[std::move(key$depth$)] = std::move(element$depth$);
                }
            }
            """,
            depth=self.depth,
            count=names.read("uvarint32", None),
            fail=names.fail(f"count{self.depth}.error()", self.where),
            container=self.container,
            target=target,
            key=lambda: self.key.read(p, f"key{self.depth}"),
            element=lambda: self.value.read(p, f"element{self.depth}"),
        )


class VariantField:
    def __init__(self, schema: Schema, node: Variant, encoding: Encoding, where: str, depth: int) -> None:
        self.where = where
        self.depth = depth
        self.cases = [
            None if case is None else make_field_generator(schema, case, encoding, where, depth + 1)
            for case in node.cases
        ]

    def fallible(self) -> bool:
        return any(case is not None and case.fallible() for case in self.cases)

    def includes(self) -> set[str]:
        return {"<variant>"}.union(*(case.includes() for case in self.cases if case is not None))

    def write(self, p: Printer, value: str) -> None:
        p.emit(names.write("uvarint32", None, f"{value}.index()"))
        p.emit("switch ($value$.index()) {", value=value)
        for index, case in enumerate(self.cases):
            p.emit("case $index$:", index=index)
            with p.indent():
                if case is not None:
                    case.write(p, f"std::get<{index}>({value})")
                p.emit("break;")
        p.emit("}")

    def read(self, p: Printer, target: str) -> None:
        p.emit("{")
        with p.indent():
            p.emit("auto tag$depth$ = $call$;", depth=self.depth, call=names.read("uvarint32", None))
            p.emit("if (!tag$depth$) $fail$", depth=self.depth, fail=names.fail(f"tag{self.depth}.error()", self.where))
            p.emit("switch (*tag$depth$) {", depth=self.depth)
            for index, case in enumerate(self.cases):
                p.emit("case $index$:", index=index)
                with p.indent():
                    p.emit("$target$.emplace<$index$>();", target=target, index=index)
                    if case is not None:
                        case.read(p, f"std::get<{index}>({target})")
                    p.emit("break;")
            p.emit("default:")
            with p.indent():
                p.emit(names.fail(names.UNKNOWN_VALUE, self.where))
            p.emit("}")
        p.emit("}")


class DuplicatedField:
    def __init__(self, element: FieldGenerator, copies: int) -> None:
        self.element = element
        self.copies = copies

    def fallible(self) -> bool:
        return self.element.fallible()

    def includes(self) -> set[str]:
        return self.element.includes()

    def write(self, p: Printer, value: str) -> None:
        p.emit(
            """
            for (std::size_t copy = 0; copy < $copies$; ++copy) {
                $body$
            }
            """,
            copies=self.copies,
            body=lambda: self.element.write(p, value),
        )

    def read(self, p: Printer, target: str) -> None:
        p.emit(
            """
            for (std::size_t copy = 0; copy < $copies$; ++copy) {
                $body$
            }
            """,
            copies=self.copies,
            body=lambda: self.element.read(p, target),
        )


def make_field_generator(schema: Schema, node: Type, encoding: Encoding, where: str, depth: int) -> FieldGenerator:
    match node:
        case Primitive():
            return PrimitiveField(node, where)
        case AliasRef():
            return AliasField(schema, node, where)
        case EnumRef():
            return EnumField(schema, node, encoding, where)
        case StructRef() | EnumName():
            return ReferenceField(schema, node, encoding, where)
        case BuiltinRef(encoded="str"):
            return BuiltinTextField(schema, node, where)
        case BuiltinRef():
            return BuiltinField(schema, node, encoding, where)
        case Literal():
            return LiteralField(schema, node, encoding, where)
        case Bitset():
            return BitsetField(schema, node, encoding, where)
        case Optional():
            return OptionalField(schema, node, encoding, where, depth)
        case List():
            return ListField(schema, node, encoding, where, depth)
        case Array():
            return ArrayField(schema, node, encoding, where, depth)
        case Map():
            return MapField(schema, node, encoding, where, depth)
        case Variant():
            return VariantField(schema, node, encoding, where, depth)
