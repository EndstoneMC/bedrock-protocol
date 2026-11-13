from itertools import groupby

from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.enum import EnumGenerator
from bedrock_protocol_compiler.cpp.expression import render
from bedrock_protocol_compiler.cpp.field import DuplicatedField, FieldGenerator, make_field_generator
from bedrock_protocol_compiler.descriptor import Field
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumShape, Schema, Shape, StructShape, reached_by


class StructGenerator:
    def __init__(self, schema: Schema, shape: StructShape) -> None:
        self.schema = schema
        self.shape = shape
        self.qualified = names.qualified(schema, shape)
        self.aliases = [(child.family.name, names.qualified(schema, child)) for child in shape.nested]
        self.defined = [shape_generator(schema, child) for child in shape.nested if child.owner is shape]
        self.members: list[tuple[str, str]] = []
        self.field_includes: set[str] = set()
        self.version = schema.versions[0] if shape.ranges[0].since is None else shape.ranges[0].since
        self.fields: list[tuple[Field, FieldGenerator]] = []
        for each in shape.fields:
            generator = make_field_generator(schema, each.type, self.version, f'"{each.name}"', 0)
            if each.copies > 1:
                generator = DuplicatedField(generator, each.copies)
            self.fields.append((each, generator))
            spelled = generator.cpp_type()
            if spelled is not None:
                self.members.append((spelled, each.name))
            self.field_includes |= generator.includes()
            self.field_includes |= {names.header(target) for target in reached_by(each)}

    def includes(self) -> set[str]:
        includes = {
            *self.field_includes,
            names.runtime("detail/reflect"),
            "<array>",
            "<cstddef>",
            "<string_view>",
        }
        if self.has_serializer:
            includes |= names.SERIALIZER_INCLUDES
        return includes.union(*(child.includes() for child in self.defined))

    @property
    def has_serializer(self) -> bool:
        return bool(self.shape.fields) or not self.shape.nested

    def definition(self, p: Printer) -> None:
        name = self.shape.family.name
        if self.defined:
            p.emit("namespace $nested$ {", nested=names.nested(name))
            p.emit("")
            for child in self.defined:
                child.definition(p)
                p.emit("")
            p.emit("}  // namespace $nested$", nested=names.nested(name))
            p.emit("")
        p.emit(
            """
            struct $name$ {
                $body$
            };
            """,
            name=name,
            body=lambda: self.body(p),
        )

    def body(self, p: Printer) -> None:
        name = self.shape.family.name
        packet_id = self.shape.family.packet_id
        for alias, spelled in self.aliases:
            p.emit("using $alias$ = $spelled$;", alias=alias, spelled=spelled)
        if self.shape.nested and (packet_id is not None or self.members):
            p.emit("")
        if packet_id is not None:
            p.emit("static constexpr int Id = $id$;", id=packet_id)
        for spelled, member in self.members:
            p.emit("$type$ $name${};", type=spelled, name=member)
        if self.shape.nested or packet_id is not None or self.members:
            p.emit("")
        p.emit("friend bool operator==(const $name$ &, const $name$ &) = default;", name=name)

    def reflection(self, p: Printer) -> None:
        for child in self.defined:
            child.reflection(p)
        members = [member for _, member in self.members]
        p.emit(
            """
            template <>
            inline constexpr bool is_reflected_struct_v<$qualified$> = true;

            template <>
            inline constexpr std::string_view struct_name_v<$qualified$>{"$name$"};

            template <>
            inline constexpr std::array<std::string_view, $count$> field_names_v<$qualified$>{{
            """,
            qualified=self.qualified,
            name=names.bare(self.shape.family),
            count=len(members),
        )
        with p.indent():
            for member in members:
                p.emit('"$name$",', name=member)
        p.emit("}};")
        p.emit("")
        if not members:
            return
        p.emit(
            """
            template <>
            struct field_accessor<$qualified$> {
                template <std::size_t I, typename S>
                static constexpr auto &get(S &value) noexcept
                {
                    $accessors$
                }
            };

            """,
            qualified=self.qualified,
            accessors=lambda: self.accessors(p, members),
        )

    def accessors(self, p: Printer, members: list[str]) -> None:
        if len(members) == 1:
            p.emit("return value.$name$;", name=members[0])
        for index, member in enumerate(members[:-1]):
            p.emit("$keyword$ constexpr (I == $index$) {", keyword="if" if index == 0 else "else if", index=index)
            with p.indent():
                p.emit("return value.$name$;", name=member)
            p.emit("}")
        if len(members) > 1:
            p.emit("else {")
            with p.indent():
                p.emit("return value.$name$;", name=members[-1])
            p.emit("}")

    def serializer_declaration(self, p: Printer) -> None:
        for child in self.defined:
            child.serializer_declaration(p)
        if not self.has_serializer:
            return
        p.emit(
            """
            template <>
            struct Serializer<$qualified$> {
                static void serialize(BinaryWriter &stream, const $qualified$ &value);
                static auto deserialize(BinaryReader &stream) -> $decoded$;
            };

            """,
            qualified=self.qualified,
            decoded=names.decoded(self.qualified),
        )

    def serializer_body(self, p: Printer) -> None:
        for child in self.defined:
            child.serializer_body(p)
        if not self.has_serializer:
            return
        p.emit(
            """
            void Serializer<$qualified$>::serialize(BinaryWriter &stream, const $qualified$ &value)
            {
                $writes$
            }

            auto Serializer<$qualified$>::deserialize(BinaryReader &stream) -> $decoded$
            {
                $qualified$ out;
                $reads$
                return out;
            }

            """,
            qualified=self.qualified,
            decoded=names.decoded(self.qualified),
            writes=lambda: self.writes(p),
            reads=lambda: self.reads(p),
        )

    def writes(self, p: Printer) -> None:
        for when, group in groupby(self.fields, key=lambda each: each[0].when):
            if when is None:
                for each, generator in group:
                    generator.write(p, f"value.{each.name}")
                continue
            p.emit("if ($condition$) {", condition=render(self.schema, self.version, when, "value"))
            with p.indent():
                for each, generator in group:
                    generator.write(p, f"value.{each.name}")
            p.emit("}")

    def reads(self, p: Printer) -> None:
        for when, group in groupby(self.fields, key=lambda each: each[0].when):
            if when is None:
                for each, generator in group:
                    generator.read(p, f"out.{each.name}")
                continue
            p.emit("if ($condition$) {", condition=render(self.schema, self.version, when, "out"))
            with p.indent():
                for each, generator in group:
                    generator.read(p, f"out.{each.name}")
            p.emit("}")


def shape_generator(schema: Schema, shape: Shape) -> StructGenerator | EnumGenerator:
    if isinstance(shape, EnumShape):
        return EnumGenerator(schema, shape)
    return StructGenerator(schema, shape)
