from functools import partial
from itertools import groupby

from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.enum import EnumGenerator, partials
from bedrock_protocol_compiler.cpp.expression import render
from bedrock_protocol_compiler.cpp.field import DuplicatedField, FieldGenerator, cpp_type, make_field_generator
from bedrock_protocol_compiler.descriptor import Field
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import Encoding, Numbering, Schema, StructModel, reached_by


class StructGenerator:
    def __init__(self, schema: Schema, model: StructModel, reached: set[Numbering]) -> None:
        self.schema = schema
        self.target = model
        self.qualified = names.qualified(schema, model)
        self.name = schema.name(model)
        self.aliases = [(child.family.name, names.qualified(schema, child)) for child in model.nested]
        self.owned = [
            (
                child,
                StructGenerator(schema, child, reached)
                if isinstance(child, StructModel)
                else EnumGenerator(schema, child, reached),
            )
            for child in model.nested
            if schema.owner(child) is model
        ]
        self.pending = dict(self.owned)
        self.members = [(cpp_type(schema, model, slot.type), slot.name) for slot in model.slots]
        self.field_includes: set[str] = set()
        self.implemented: list[tuple[Encoding, list[tuple[Field, FieldGenerator]]]] = []
        for encoding in schema.encodings(model):
            if not encoding.fields and model.nested:
                continue
            fields: list[tuple[Field, FieldGenerator]] = []
            for each in encoding.fields:
                generator = make_field_generator(schema, each.type, encoding, f'"{each.name}"', 0)
                if each.duplicate > 1:
                    generator = DuplicatedField(generator, each.duplicate)
                fields.append((each, generator))
                self.field_includes |= generator.includes()
                self.field_includes |= {names.header(target) for target in reached_by(each)}
            self.implemented.append((encoding, fields))

    def includes(self) -> set[str]:
        includes = {
            *self.field_includes,
            names.runtime("detail/reflect"),
            "<array>",
            "<cstddef>",
            "<string_view>",
        }
        if self.implemented:
            includes |= names.SERIALIZER_INCLUDES
        return includes.union(*(child.includes() for _, child in self.owned))

    def nested(
        self,
        p: Printer,
        children: "list[StructGenerator | EnumGenerator]",
        outer: "tuple[StructGenerator, ...]" = (),
    ) -> None:
        scopes = [names.nested(each.name) for each in (*outer, self)]
        for scope in scopes:
            p.emit("namespace $nested$ {", nested=scope)
            p.emit("")
        for child in children:
            child.definition(p)
            p.emit("")
        for scope in reversed(scopes):
            p.emit("}  // namespace $nested$", nested=scope)
            p.emit("")

    def definition(self, p: Printer) -> None:
        if self.pending:
            self.nested(p, list(self.pending.values()))
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
        for spelled, member in self.members:
            p.emit("$type$ $name${};", type=spelled, name=member)
        if self.target.nested or packet_id is not None or self.members:
            p.emit("")
        p.emit("friend bool operator==(const $name$ &, const $name$ &) = default;", name=self.name)

    def reflection(self, p: Printer) -> None:
        for _, child in self.owned:
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
        for _, child in self.owned:
            child.serializer_declaration(p)
        for encoding, _ in self.implemented:
            serializer = names.serializer(self.qualified, encoding.since, encoding.mode)
            p.emit(
                """
                template <>
                struct $serializer$ {
                    static constexpr int since = $since$;
                    static auto serialize(BinaryWriter &stream, const $qualified$ &value) -> $encoded$;
                    static auto deserialize(BinaryReader &stream) -> $decoded$;
                };

                """,
                serializer=serializer,
                since=encoding.since,
                qualified=self.qualified,
                encoded=names.ENCODED,
                decoded=names.decoded(self.qualified),
            )
            partials(p, self.schema, self.qualified, serializer, encoding.served)

    def serializer_body(self, p: Printer) -> None:
        for _, child in self.owned:
            child.serializer_body(p)
        for encoding, fields in self.implemented:
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
                serializer=names.serializer(self.qualified, encoding.since, encoding.mode),
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
