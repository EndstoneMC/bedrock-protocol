from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.field import primitive_includes
from bedrock_protocol_compiler.descriptor import Binary, Int, MemberRef, Range
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumModel, Numbering, Schema, SerializationMode


def partials(p: Printer, qualified: str, implementation: str, served: dict[SerializationMode, list[Range]]) -> None:
    for mode, runs in served.items():
        for run in runs:
            p.emit(
                """
                template <int V>$requirement$
                struct $head$ : $implementation$ {};

                """,
                requirement=names.requirement(run),
                head=names.serializer(qualified, "V", mode),
                implementation=implementation,
            )


class EnumGenerator:
    def __init__(self, schema: Schema, enum_type: EnumModel, reached: set[Numbering]) -> None:
        self.schema = schema
        self.target = enum_type
        self.qualified = names.qualified(schema, enum_type)
        self.underlying = names.PRIMITIVES[enum_type.underlying.name]
        self.enumerators = schema.enumerators(enum_type)
        self.namings = schema.namings(enum_type)
        self.stem = names.bare(schema, enum_type).replace("::", "_")
        self.numberings = [numbering for numbering in schema.numberings(enum_type) if numbering in reached]

    def includes(self) -> set[str]:
        includes = {names.runtime("enum"), "<array>", "<string_view>"} | primitive_includes(self.target.underlying)
        if self.namings:
            includes |= names.SERIALIZER_INCLUDES
        if len(self.namings) > 1:
            includes.add(names.runtime("detail/naming"))
        if self.numberings:
            includes.add(names.runtime("detail/numbering"))
        return includes

    def spell(self, number: int) -> str:
        if number < 0 and self.underlying.startswith("std::uint"):
            return f"static_cast<{self.underlying}>({number})"
        return str(number)

    def definition(self, p: Printer) -> None:
        cpp_names = {member.name: member.cpp_name for member in self.target.members if not member.deprecated}
        p.emit("enum class $name$ : $underlying$ {", name=self.target.family.name, underlying=self.underlying)
        with p.indent():
            for member in self.target.members:
                number = self.enumerators[member.name]
                match member.value:
                    case MemberRef(name=name) if name in cpp_names:
                        spelled = cpp_names[name]
                    case Binary(left=MemberRef(name=name), right=Int(value=offset)) if name in cpp_names:
                        spelled = f"{cpp_names[name]} - {offset}"
                    case _:
                        spelled = self.spell(number)
                attribute = " [[deprecated]]" if member.deprecated else ""
                p.emit("$name$$attribute$ = $value$,", name=member.cpp_name, attribute=attribute, value=spelled)
        p.emit("};")

    def reflection(self, p: Printer) -> None:
        if not self.target.members:
            return
        members = self.target.members
        values = [
            f"static_cast<{self.qualified}>({self.enumerators[member.name]})"
            if member.deprecated
            else f"{self.qualified}::{member.cpp_name}"
            for member in members
        ]
        tables = [
            ("values_v", self.qualified, values),
            ("names_v", "std::string_view", [f'"{member.encoded_name}"' for member in members]),
            ("schema_names_v", "std::string_view", [f'"{member.name}"' for member in members]),
        ]
        if any(member.deprecated for member in members):
            tables.append(("deprecated_v", "bool", [str(member.deprecated).lower() for member in members]))
        for table, element, rows in tables:
            p.emit(
                """
                template <>
                inline constexpr std::array<$element$, $count$> $table$<$qualified$>{{
                """,
                element=element,
                count=len(rows),
                table=table,
                qualified=self.qualified,
            )
            with p.indent():
                for row in rows:
                    p.emit("$row$,", row=row)
            p.emit("}};")
            p.emit("")
        p.emit(
            """
            template <>
            inline constexpr std::string_view type_name_v<$qualified$>{"$name$"};

            """,
            qualified=self.qualified,
            name=names.bare(self.schema, self.target),
        )
        pair = f"NumberPair<{self.qualified}>"
        for numbering in self.numberings:
            p.emit(
                """
                template <>
                struct Numbering<$qualified$, $since$> {
                """,
                qualified=self.qualified,
                since=numbering.since,
            )
            tables = [
                ("encoded", pair, [self.pair(each) for each in sorted(numbering.encoded.items())]),
                ("decoded", pair, [self.pair(each) for each in sorted(numbering.decoded.items())]),
                ("absent", self.underlying, [self.spell(each) for each in sorted(numbering.absent)]),
                ("lossy", self.underlying, [self.spell(each) for each in sorted(numbering.lossy)]),
            ]
            with p.indent():
                for table, element, rows in tables:
                    p.emit(
                        "static constexpr std::array<$element$, $count$> $table$$body$;",
                        element=element,
                        count=len(rows),
                        table=table,
                        body=f"{{{{{', '.join(rows)}}}}}" if rows else "{}",
                    )
            p.emit("};")
            p.emit("")

    def pair(self, entry: tuple[int, int]) -> str:
        return f"{{{self.spell(entry[0])}, {self.spell(entry[1])}}}"

    def serializer_declaration(self, p: Printer) -> None:
        for naming in self.namings:
            serializer = names.serializer(self.qualified, naming.since)
            p.emit(
                """
                template <>
                struct $serializer$ {
                    static auto serialize(BinaryWriter &stream, $qualified$ value) -> $encoded$;
                    static auto deserialize(BinaryReader &stream) -> $decoded$;
                };

                """,
                serializer=serializer,
                qualified=self.qualified,
                encoded=names.ENCODED,
                decoded=names.decoded(self.qualified),
            )
            partials(p, self.qualified, serializer, {SerializationMode.DEFAULT: naming.runs})

    def serializer_body(self, p: Printer) -> None:
        if len(self.namings) > 1:
            spelled = {
                self.enumerators[member.name]: f"{self.qualified}::{member.cpp_name}"
                for member in reversed(self.target.members)
                if not member.deprecated
            }
            p.emit("namespace detail {")
            p.emit("")
            for naming in self.namings:
                tables = [
                    ("written", sorted(naming.written.items())),
                    ("read", sorted((value, name) for name, value in naming.read.items())),
                ]
                for table, rows in tables:
                    p.emit(
                        """
                        constexpr std::array<NameEntry<$qualified$>, $count$> naming_$since$_$stem$_$table${{
                        """,
                        qualified=self.qualified,
                        count=len(rows),
                        since=naming.since,
                        stem=self.stem,
                        table=table,
                    )
                    with p.indent():
                        for value, name in rows:
                            p.emit('{$value$, "$name$"},', value=spelled[value], name=name)
                    p.emit("}};")
                    p.emit("")
            p.emit("}  // namespace detail")
            p.emit("")
        unknown = names.unexpected(names.UNKNOWN_VALUE)
        for naming in self.namings:
            serializer = names.serializer(self.qualified, naming.since)
            table = f"detail::naming_{naming.since}_{self.stem}"
            p.emit(
                "auto $serializer$::serialize(BinaryWriter &stream, $qualified$ value) -> $encoded$",
                serializer=serializer,
                qualified=self.qualified,
                encoded=names.ENCODED,
            )
            p.emit("{")
            with p.indent():
                if len(self.namings) == 1:
                    p.emit("if (!enum_contains(value)) $unknown$", unknown=unknown)
                    p.emit(names.write("str", None, "enum_name(value)"))
                else:
                    p.emit("const auto name = detail::name_of($table$_written, value);", table=table)
                    p.emit("if (!name) $unknown$", unknown=unknown)
                    p.emit(names.write("str", None, "*name"))
                p.emit("return {};")
            p.emit("}")
            p.emit("")
            p.emit(
                "auto $serializer$::deserialize(BinaryReader &stream) -> $decoded$",
                serializer=serializer,
                decoded=names.decoded(self.qualified),
            )
            p.emit("{")
            with p.indent():
                p.emit("auto v = $read$;", read=names.read("str", None))
                p.emit("if (!v) $failure$", failure=names.unexpected("v.error()"))
                if len(self.namings) == 1:
                    p.emit("const auto value = enum_cast<$qualified$>(*v);", qualified=self.qualified)
                else:
                    p.emit("const auto value = detail::value_of($table$_read, *v);", table=table)
                p.emit("if (!value) $unknown$", unknown=unknown)
                p.emit("return *value;")
            p.emit("}")
            p.emit("")
