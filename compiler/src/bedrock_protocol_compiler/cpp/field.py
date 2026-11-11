from typing import Protocol

from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.descriptor import (
    AliasRef,
    Array,
    Bitset,
    BuiltinRef,
    EnumName,
    EnumRef,
    Int,
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
from bedrock_protocol_compiler.schema import EnumShape, Schema


class FieldGenerator(Protocol):
    def cpp_type(self) -> str | None: ...

    def includes(self) -> set[str]: ...


class PrimitiveField:
    def __init__(self, node: Primitive) -> None:
        self.node = node

    def cpp_type(self) -> str:
        return names.PRIMITIVES[self.node.name]

    def includes(self) -> set[str]:
        if self.node.name == "str":
            return {"<string>"}
        if self.node.name == "bytes":
            return {"<cstddef>", "<vector>"}
        return {"<cstdint>"} if self.cpp_type().startswith("std::") else set()


class AliasField:
    def __init__(self, schema: Schema, node: AliasRef) -> None:
        self.schema = schema
        self.node = node

    def cpp_type(self) -> str:
        return names.qualified(self.schema, self.node.alias)

    def includes(self) -> set[str]:
        return {names.header(self.node.alias)}


class ReferenceField:
    def __init__(self, schema: Schema, node: StructRef | EnumRef | EnumName, version: int) -> None:
        self.schema = schema
        self.family = node.struct if isinstance(node, StructRef) else node.enum
        self.version = version

    def cpp_type(self) -> str:
        return names.qualified(self.schema, self.schema.shape_at(self.family, self.version))

    def includes(self) -> set[str]:
        return {names.header(self.family)}


class BuiltinField:
    def __init__(self, schema: Schema, node: BuiltinRef) -> None:
        self.schema = schema
        self.node = node

    def cpp_type(self) -> str:
        return names.qualified(self.schema, self.node.builtin)

    def includes(self) -> set[str]:
        return {names.header(self.node.builtin)}


class LiteralField:
    def __init__(self, node: Literal) -> None:
        self.node = node

    def cpp_type(self) -> None:
        return None

    def includes(self) -> set[str]:
        if isinstance(self.node.value, MemberRef):
            return {names.header(self.node.value.enum)}
        return set()


class BitsetField:
    def __init__(self, schema: Schema, node: Bitset, version: int) -> None:
        self.node = node
        shape = schema.shape_at(node.width.enum, version)
        assert isinstance(shape, EnumShape)
        (member,) = (each for each in shape.members if each.name == node.width.name)
        assert isinstance(member.value, Int)
        self.width = member.value.value

    def cpp_type(self) -> str:
        return f"std::bitset<{self.width}>"

    def includes(self) -> set[str]:
        return {"<bitset>", names.header(self.node.width.enum)}


class OptionalField:
    def __init__(self, schema: Schema, node: Optional, version: int) -> None:
        self.element = make_field_generator(schema, node.element, version)

    def cpp_type(self) -> str:
        return f"std::optional<{self.element.cpp_type()}>"

    def includes(self) -> set[str]:
        return {"<optional>"} | self.element.includes()


class ListField:
    def __init__(self, schema: Schema, node: List, version: int) -> None:
        self.element = make_field_generator(schema, node.element, version)

    def cpp_type(self) -> str:
        return f"std::vector<{self.element.cpp_type()}>"

    def includes(self) -> set[str]:
        return {"<vector>"} | self.element.includes()


class ArrayField:
    def __init__(self, schema: Schema, node: Array, version: int) -> None:
        self.node = node
        self.element = make_field_generator(schema, node.element, version)

    def cpp_type(self) -> str:
        return f"std::array<{self.element.cpp_type()}, {self.node.size}>"

    def includes(self) -> set[str]:
        return {"<array>"} | self.element.includes()


class MapField:
    def __init__(self, schema: Schema, node: Map, version: int) -> None:
        self.key = make_field_generator(schema, node.key, version)
        self.value = make_field_generator(schema, node.value, version)

    def cpp_type(self) -> str:
        return f"std::map<{self.key.cpp_type()}, {self.value.cpp_type()}>"

    def includes(self) -> set[str]:
        return {"<map>"} | self.key.includes() | self.value.includes()


class VariantField:
    def __init__(self, schema: Schema, node: Variant, version: int) -> None:
        self.cases = [None if case is None else make_field_generator(schema, case, version) for case in node.cases]

    def cpp_type(self) -> str:
        cases = ("std::monostate" if case is None else f"{case.cpp_type()}" for case in self.cases)
        return f"std::variant<{', '.join(cases)}>"

    def includes(self) -> set[str]:
        return {"<variant>"}.union(*(case.includes() for case in self.cases if case is not None))


def make_field_generator(schema: Schema, node: Type, version: int) -> FieldGenerator:
    match node:
        case Primitive():
            return PrimitiveField(node)
        case AliasRef():
            return AliasField(schema, node)
        case StructRef() | EnumRef() | EnumName():
            return ReferenceField(schema, node, version)
        case BuiltinRef():
            return BuiltinField(schema, node)
        case Literal():
            return LiteralField(node)
        case Bitset():
            return BitsetField(schema, node, version)
        case Optional():
            return OptionalField(schema, node, version)
        case List():
            return ListField(schema, node, version)
        case Array():
            return ArrayField(schema, node, version)
        case Map():
            return MapField(schema, node, version)
        case Variant():
            return VariantField(schema, node, version)
