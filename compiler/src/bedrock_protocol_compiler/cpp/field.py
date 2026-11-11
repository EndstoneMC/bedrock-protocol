import json
from typing import Protocol

from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.expression import render_count
from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    Array,
    Bitset,
    BuiltinRef,
    EnumName,
    EnumRef,
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
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumShape, Schema

ENUM_WIRES = {
    "bool": "bool",
    "int8": "int8",
    "uint8": "uint8",
    "int16": "varint32",
    "uint16": "uvarint32",
    "int32": "varint32",
    "uint32": "uvarint32",
}


def underlying_of(shape: EnumShape) -> str:
    return "int32" if shape.underlying is None else shape.underlying.name


def primitive_includes(node: Primitive) -> set[str]:
    if node.name == "str":
        return {"<string>"}
    if node.name == "bytes":
        return {"<cstddef>", "<vector>"}
    return {"<cstdint>"} if names.PRIMITIVES[node.name].startswith("std::") else set()


class FieldGenerator(Protocol):
    def cpp_type(self) -> str | None: ...

    def includes(self) -> set[str]: ...

    def write(self, p: Printer, value: str) -> None: ...

    def read(self, p: Printer, target: str) -> None: ...


class ScalarField:
    def __init__(self, where: str, spelled: str, stored: str, wire: str, endian: str | None) -> None:
        self.where = where
        self.spelled = spelled
        self.stored = stored
        self.wire = wire
        self.endian = endian

    def cpp_type(self) -> str:
        return self.spelled

    def write(self, p: Printer, value: str) -> None:
        p.emit(names.write(self.wire, self.endian, value))

    def read(self, p: Printer, target: str) -> None:
        p.emit("{")
        with p.indent():
            p.emit("auto v = $call$;", call=names.read(self.wire, self.endian))
            p.emit("if (!v) $fail$", fail=names.fail("v.error()", self.where))
            if self.wire in ("str", "bytes"):
                p.emit("$target$ = std::move(*v);", target=target)
            elif self.spelled == names.PRIMITIVES[self.wire]:
                p.emit("$target$ = *v;", target=target)
            else:
                p.emit("$target$ = static_cast<$type$>(*v);", target=target, type=self.spelled)
            if names.PRIMITIVES[self.stored] != names.PRIMITIVES[self.wire]:
                p.emit(
                    "if (static_cast<$wire$>($target$) != *v) $fail$",
                    wire=names.PRIMITIVES[self.wire],
                    target=target,
                    fail=names.fail(names.OUT_OF_RANGE, self.where),
                )
        p.emit("}")


class PrimitiveField(ScalarField):
    def __init__(self, node: Primitive, where: str) -> None:
        super().__init__(where, names.PRIMITIVES[node.name], node.name, node.wire or node.name, node.endian)
        self.node = node

    def includes(self) -> set[str]:
        return primitive_includes(self.node)


class AliasField(ScalarField):
    def __init__(self, schema: Schema, node: AliasRef, where: str) -> None:
        stored = node.alias.primitive.name
        super().__init__(where, names.qualified(schema, node.alias), stored, node.wire or stored, None)
        self.node = node

    def includes(self) -> set[str]:
        return {names.header(self.node.alias)}


class EnumField(ScalarField):
    def __init__(self, schema: Schema, node: EnumRef, version: int, where: str) -> None:
        shape = schema.shape_at(node.enum, version)
        assert isinstance(shape, EnumShape)
        stored = underlying_of(shape)
        super().__init__(where, names.qualified(schema, shape), stored, node.wire or ENUM_WIRES[stored], node.endian)
        self.node = node

    def includes(self) -> set[str]:
        return {names.header(self.node.enum)}


class SerializerField:
    def __init__(self, where: str, spelled: str) -> None:
        self.where = where
        self.spelled = spelled

    def cpp_type(self) -> str:
        return self.spelled

    def write(self, p: Printer, value: str) -> None:
        p.emit("Serializer<$type$>::serialize(stream, $value$);", type=self.spelled, value=value)

    def read(self, p: Printer, target: str) -> None:
        p.emit(
            """
            {
                auto v = Serializer<$type$>::deserialize(stream);
                if (!v) $fail$
                $target$ = std::move(*v);
            }
            """,
            type=self.spelled,
            fail=names.fail("v.error()", self.where),
            target=target,
        )


class ReferenceField(SerializerField):
    def __init__(self, schema: Schema, node: StructRef | EnumName, version: int, where: str) -> None:
        self.family = node.struct if isinstance(node, StructRef) else node.enum
        super().__init__(where, names.qualified(schema, schema.shape_at(self.family, version)))

    def includes(self) -> set[str]:
        return {names.header(self.family)}


class BuiltinField(SerializerField):
    def __init__(self, schema: Schema, node: BuiltinRef, where: str) -> None:
        super().__init__(where, names.qualified(schema, node.builtin))
        self.node = node

    def includes(self) -> set[str]:
        return {names.header(self.node.builtin)}


class BitsetField(SerializerField):
    def __init__(self, schema: Schema, node: Bitset, version: int, where: str) -> None:
        shape = schema.shape_at(node.width.enum, version)
        assert isinstance(shape, EnumShape)
        super().__init__(where, f"std::bitset<{shape.numbers[node.width.name]}>")
        self.node = node

    def includes(self) -> set[str]:
        return {"<bitset>", names.runtime("detail/bitset"), names.header(self.node.width.enum)}


class LiteralField:
    def __init__(self, schema: Schema, node: Literal, version: int, where: str) -> None:
        self.node = node
        self.where = where
        match node.value:
            case bool(flag):
                self.wire = "bool"
                self.constant = "true" if flag else "false"
                self.expected = self.constant
            case str(text):
                self.wire = "str"
                self.constant = json.dumps(text)
                self.expected = self.constant
            case MemberRef() as member:
                shape = schema.shape_at(member.enum, version)
                assert isinstance(shape, EnumShape)
                self.wire = ENUM_WIRES[underlying_of(shape)]
                self.constant = names.enumerator(schema, member, version)
                self.expected = f"static_cast<{names.PRIMITIVES[self.wire]}>({self.constant})"

    def cpp_type(self) -> None:
        return None

    def includes(self) -> set[str]:
        if isinstance(self.node.value, MemberRef):
            return {names.header(self.node.value.enum)}
        return set()

    def write(self, p: Printer, value: str) -> None:
        p.emit(names.write(self.wire, None, self.constant))

    def read(self, p: Printer, target: str) -> None:
        p.emit(
            """
            {
                auto v = $call$;
                if (!v) $fail$
                if (*v != $expected$) $mismatch$
            }
            """,
            call=names.read(self.wire, None),
            fail=names.fail("v.error()", self.where),
            expected=self.expected,
            mismatch=names.fail(names.UNKNOWN_VALUE, self.where),
        )


class OptionalField:
    def __init__(self, schema: Schema, node: Optional, version: int, where: str, depth: int) -> None:
        self.element = make_field_generator(schema, node.element, version, where, depth)
        self.where = where
        self.depth = depth

    def cpp_type(self) -> str:
        return f"std::optional<{self.element.cpp_type()}>"

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
    def __init__(self, schema: Schema, node: List, version: int, where: str, depth: int) -> None:
        self.schema = schema
        self.node = node
        self.version = version
        self.where = where
        self.depth = depth
        self.element = make_field_generator(schema, node.element, version, f"{where}, i{depth}", depth + 1)

    def cpp_type(self) -> str:
        return f"std::vector<{self.element.cpp_type()}>"

    def includes(self) -> set[str]:
        return {"<vector>"} | self.element.includes()

    def write(self, p: Printer, value: str) -> None:
        if self.node.prefix is not None:
            p.emit(names.write(self.node.prefix.name, self.node.prefix.endian, f"{value}.size()"))
        p.emit(
            """
            for (const auto &e$depth$ : $value$) {
                $body$
            }
            """,
            depth=self.depth,
            value=value,
            body=lambda: self.element.write(p, f"e{self.depth}"),
        )

    def read(self, p: Printer, target: str) -> None:
        if self.node.prefix is not None:
            count = names.read(self.node.prefix.name, self.node.prefix.endian)
        else:
            assert self.node.count is not None
            count = render_count(self.schema, self.version, self.node.count, "out")
        p.emit(
            """
            {
                auto count$depth$ = $count$;
                if (!count$depth$) $fail$
                auto budget$depth$ = $account$;
                if (!budget$depth$) $budget_fail$
                $target$.reserve(static_cast<std::size_t>(*count$depth$));
                for (std::size_t i$depth$ = 0; i$depth$ < static_cast<std::size_t>(*count$depth$); ++i$depth$) {
                    $target$.emplace_back();
                    $body$
                }
            }
            """,
            depth=self.depth,
            count=count,
            fail=names.fail(f"count{self.depth}.error()", self.where),
            account=names.account(f"*count{self.depth}", self.cpp_type()),
            budget_fail=names.fail(f"budget{self.depth}.error()", self.where),
            target=target,
            body=lambda: self.element.read(p, f"{target}.back()"),
        )


class ArrayField:
    def __init__(self, schema: Schema, node: Array, version: int, where: str, depth: int) -> None:
        self.node = node
        self.where = where
        self.depth = depth
        self.element = make_field_generator(schema, node.element, version, f"{where}, i{depth}", depth + 1)

    def cpp_type(self) -> str:
        return f"std::array<{self.element.cpp_type()}, {self.node.size}>"

    def includes(self) -> set[str]:
        return {"<array>"} | self.element.includes()

    def write(self, p: Printer, value: str) -> None:
        p.emit(
            """
            for (const auto &e$depth$ : $value$) {
                $body$
            }
            """,
            depth=self.depth,
            value=value,
            body=lambda: self.element.write(p, f"e{self.depth}"),
        )

    def read(self, p: Printer, target: str) -> None:
        p.emit(
            """
            {
                auto budget$depth$ = $account$;
                if (!budget$depth$) $fail$
                for (std::size_t i$depth$ = 0; i$depth$ < $size$; ++i$depth$) {
                    $body$
                }
            }
            """,
            depth=self.depth,
            size=self.node.size,
            account=names.account(str(self.node.size), self.cpp_type()),
            fail=names.fail(f"budget{self.depth}.error()", self.where),
            body=lambda: self.element.read(p, f"{target}[i{self.depth}]"),
        )


class MapField:
    def __init__(self, schema: Schema, node: Map, version: int, where: str, depth: int) -> None:
        self.where = where
        self.depth = depth
        self.key = make_field_generator(schema, node.key, version, f"{where}, i{depth}", depth + 1)
        self.value = make_field_generator(schema, node.value, version, f"{where}, i{depth}", depth + 1)

    def cpp_type(self) -> str:
        return f"std::map<{self.key.cpp_type()}, {self.value.cpp_type()}>"

    def includes(self) -> set[str]:
        return {"<map>"} | self.key.includes() | self.value.includes()

    def write(self, p: Printer, value: str) -> None:
        p.emit(names.write("uvarint32", None, f"{value}.size()"))
        p.emit(
            """
            for (const auto &[k$depth$, v$depth$] : $value$) {
                $key$
                $element$
            }
            """,
            depth=self.depth,
            value=value,
            key=lambda: self.key.write(p, f"k{self.depth}"),
            element=lambda: self.value.write(p, f"v{self.depth}"),
        )

    def read(self, p: Printer, target: str) -> None:
        p.emit(
            """
            {
                auto count$depth$ = $count$;
                if (!count$depth$) $fail$
                auto budget$depth$ = $account$;
                if (!budget$depth$) $budget_fail$
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
            account=names.account(f"*count{self.depth}", self.cpp_type()),
            container=self.cpp_type(),
            target=target,
            budget_fail=names.fail(f"budget{self.depth}.error()", self.where),
            key=lambda: self.key.read(p, f"key{self.depth}"),
            element=lambda: self.value.read(p, f"element{self.depth}"),
        )


class VariantField:
    def __init__(self, schema: Schema, node: Variant, version: int, where: str, depth: int) -> None:
        self.where = where
        self.depth = depth
        self.cases = [
            None if case is None else make_field_generator(schema, case, version, where, depth + 1)
            for case in node.cases
        ]

    def cpp_type(self) -> str:
        cases = ("std::monostate" if case is None else f"{case.cpp_type()}" for case in self.cases)
        return f"std::variant<{', '.join(cases)}>"

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


def make_field_generator(schema: Schema, node: Type, version: int, where: str, depth: int) -> FieldGenerator:
    match node:
        case Primitive():
            return PrimitiveField(node, where)
        case AliasRef():
            return AliasField(schema, node, where)
        case EnumRef():
            return EnumField(schema, node, version, where)
        case StructRef() | EnumName():
            return ReferenceField(schema, node, version, where)
        case BuiltinRef():
            return BuiltinField(schema, node, where)
        case Literal():
            return LiteralField(schema, node, version, where)
        case Bitset():
            return BitsetField(schema, node, version, where)
        case Optional():
            return OptionalField(schema, node, version, where, depth)
        case List():
            return ListField(schema, node, version, where, depth)
        case Array():
            return ArrayField(schema, node, version, where, depth)
        case Map():
            return MapField(schema, node, version, where, depth)
        case Variant():
            return VariantField(schema, node, version, where, depth)
