from functools import partial
from itertools import groupby

from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.enum import EnumGenerator, partials
from bedrock_protocol_compiler.cpp.expression import render
from bedrock_protocol_compiler.cpp.field import (
    DuplicatedField,
    FieldGenerator,
    cpp_type,
    cpp_type_includes,
    make_field_generator,
)
from bedrock_protocol_compiler.descriptor import EnumName, EnumRef, Expression, Field, Int
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import Encoding, Schema, StructModel, reached_by


class StructGenerator:
    def __init__(self, schema: Schema, model: StructModel) -> None:
        self.schema = schema
        self.target = model
        self.qualified = names.qualified(schema, model)
        self.name = schema.name(model)
        self.aliases = [(child.family.name, names.qualified(schema, child)) for child in model.nested]
        self.owned = [
            (
                child,
                StructGenerator(schema, child) if isinstance(child, StructModel) else EnumGenerator(schema, child),
            )
            for child in model.nested
            if schema.owner(child) is model
        ]
        self.members: list[tuple[str, str, str]] = []
        self.declared_includes = {names.header(child.family) for child in model.nested}
        for slot in model.slots:
            spelled = cpp_type(schema, model, slot.type)
            marked = schema.default_member(model, slot.type) if isinstance(slot.type, EnumRef | EnumName) else None
            self.members.append((spelled, slot.name, "" if marked is None else f"{spelled}::{marked.cpp_name}"))
            self.declared_includes |= cpp_type_includes(slot.type)
        self.field_includes: set[str] = set()
        self.implemented: list[tuple[Encoding, list[tuple[Field, FieldGenerator]]]] = []
        for encoding in schema.encodings(model):
            if not encoding.fields and model.nested and encoding.excluded is None:
                continue
            if encoding.manual:
                self.declared_includes.add("<cstdint>")
            fields: list[tuple[Field, FieldGenerator]] = []
            for each in encoding.fields:
                generator = make_field_generator(schema, each.type, encoding, f'"{each.name}"', 0)
                if each.duplicate is not None:
                    generator = DuplicatedField(
                        generator,
                        self.copies(encoding, each.duplicate, "value"),
                        self.copies(encoding, each.duplicate, "out"),
                    )
                fields.append((each, generator))
                self.field_includes |= generator.includes()
                self.field_includes |= {names.header(target) for target in reached_by(each)}
                if each.when is not None:
                    self.field_includes.add("<cstdint>")
            self.field_includes |= {
                names.runtime(child.model.family.module)
                for child in encoding.reached.values()
                if isinstance(child, Encoding) and child.manual
            }
            self.implemented.append((encoding, fields))

    def copies(self, encoding: Encoding, copies: Expression, receiver: str) -> str:
        if isinstance(copies, Int):
            return str(copies.value)
        return f"static_cast<std::size_t>({render(self.schema, encoding, copies, receiver)})"

    def includes(self) -> set[str]:
        includes = {
            *self.declared_includes,
            names.runtime("detail/reflect"),
            "<array>",
            "<cstddef>",
            "<string_view>",
        }
        if self.implemented:
            includes |= names.SERIALIZER_INCLUDES
        return includes

    def definition(self, p: Printer) -> None:
        packet_id = self.target.family.packet_id
        p.emit(
            """
            struct $name$ {
                $body$
            };
            """,
            name=self.name,
            body=lambda: self.body(p, packet_id),
        )

    def body(self, p: Printer, packet_id: int | None) -> None:
        for alias, spelled in self.aliases:
            p.emit("using $alias$ = $spelled$;", alias=alias, spelled=spelled)
        if self.target.nested and (packet_id is not None or self.members):
            p.emit("")
        if packet_id is not None:
            p.emit("static constexpr int Id = $id$;", id=packet_id)
        for spelled, member, initial in self.members:
            p.emit("$type$ $name${$initial$};", type=spelled, name=member, initial=initial)
        if self.target.nested or packet_id is not None or self.members:
            p.emit("")
        p.emit("friend bool operator==(const $name$ &, const $name$ &) = default;", name=self.name)

    def reflection(self, p: Printer) -> None:
        members = [member for _, member, _ in self.members]
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
            name=names.bare(self.schema, self.target),
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
        for encoding, _ in self.implemented:
            serializer = names.serializer(self.qualified, encoding.since, encoding.mode, encoding.excluded)
            p.emit(
                """
                template <>
                struct $serializer$ {
                    static constexpr int since = $since$;
                    $static$ auto serialize(BinaryWriter &stream, const $qualified$ &value$argument$) -> $encoded$;
                    $static$ auto deserialize(BinaryReader &stream$argument$) -> $decoded$;
                };

                """,
                serializer=serializer,
                since=encoding.since,
                static="static inline" if encoding.manual else "static",
                qualified=self.qualified,
                argument=", std::int64_t argument" if encoding.manual else "",
                encoded=names.ENCODED,
                decoded=names.decoded(self.qualified),
            )
            partials(p, self.schema, self.qualified, serializer, encoding.served)

    def serializer_body(self, p: Printer) -> None:
        for _, child in self.owned:
            child.serializer_body(p)
        for encoding, fields in self.implemented:
            if encoding.manual:
                continue
            p.emit(
                """
                auto $serializer$::serialize(BinaryWriter &stream, const $qualified$ &value) -> $encoded$
                {
                    $writes$
                    return {};
                }

                auto $serializer$::deserialize(BinaryReader &stream) -> $decoded$
                {
                    $qualified$ out;
                    $reads$
                    return out;
                }

                """,
                serializer=names.serializer(self.qualified, encoding.since, encoding.mode, encoding.excluded),
                qualified=self.qualified,
                encoded=names.ENCODED,
                decoded=names.decoded(self.qualified),
                writes=partial(self.writes, p, encoding, fields),
                reads=partial(self.reads, p, encoding, fields),
            )

    def writes(self, p: Printer, encoding: Encoding, fields: list[tuple[Field, FieldGenerator]]) -> None:
        for when, group in groupby(fields, key=lambda each: each[0].when):
            if when is None:
                for each, generator in group:
                    generator.write(p, f"value.{each.name}")
                continue
            p.emit("if ($condition$) {", condition=render(self.schema, encoding, when, "value"))
            with p.indent():
                for each, generator in group:
                    generator.write(p, f"value.{each.name}")
            p.emit("}")

    def reads(self, p: Printer, encoding: Encoding, fields: list[tuple[Field, FieldGenerator]]) -> None:
        for when, group in groupby(fields, key=lambda each: each[0].when):
            if when is None:
                for each, generator in group:
                    generator.read(p, f"out.{each.name}")
                continue
            p.emit("if ($condition$) {", condition=render(self.schema, encoding, when, "out"))
            with p.indent():
                for each, generator in group:
                    generator.read(p, f"out.{each.name}")
            p.emit("}")
