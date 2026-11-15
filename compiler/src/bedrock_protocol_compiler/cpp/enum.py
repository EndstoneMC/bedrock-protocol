from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.field import primitive_includes
from bedrock_protocol_compiler.descriptor import Binary, Int, MemberRef, Range
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumModel, EnumType, Schema, SerializationMode


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
    def __init__(self, schema: Schema, enum_type: EnumType) -> None:
        self.schema = schema
        self.target = enum_type
        self.qualified = names.qualified(schema, enum_type)
        self.serializer = names.serializer(self.qualified, names.since(schema, enum_type))
        self.underlying = names.PRIMITIVES[enum_type.underlying.name]
        self.enumerators = schema.enumerators(enum_type)
        forms = enum_type.runs if isinstance(enum_type, EnumModel) else [enum_type.family]
        self.name_coded = any(form in schema.name_coded for form in forms)

    def includes(self) -> set[str]:
        includes = {names.runtime("enum"), "<array>", "<string_view>"} | primitive_includes(self.target.underlying)
        if self.name_coded:
            includes |= names.SERIALIZER_INCLUDES
        return includes

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
                    case _ if number < 0 and self.underlying.startswith("std::uint"):
                        spelled = f"static_cast<{self.underlying}>({number})"
                    case _:
                        spelled = str(number)
                attribute = " [[deprecated]]" if member.deprecated else ""
                p.emit("$name$$attribute$ = $value$,", name=member.cpp_name, attribute=attribute, value=spelled)
        p.emit("};")

    def reflection(self, p: Printer) -> None:
        if not self.target.members:
            return
        members = sorted(self.target.members, key=lambda member: not isinstance(member.value, MemberRef | Binary))
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

    def serializer_declaration(self, p: Printer) -> None:
        if not self.name_coded:
            return
        p.emit(
            """
            template <>
            struct $serializer$ {
                static auto serialize(BinaryWriter &stream, $qualified$ value) -> $encoded$;
                static auto deserialize(BinaryReader &stream) -> $decoded$;
            };

            """,
            serializer=self.serializer,
            qualified=self.qualified,
            encoded=names.ENCODED,
            decoded=names.decoded(self.qualified),
        )
        partials(p, self.qualified, self.serializer, {SerializationMode.DEFAULT: self.schema.enum_runs(self.target)})

    def serializer_body(self, p: Printer) -> None:
        if not self.name_coded:
            return
        p.emit(
            """
            auto $serializer$::serialize(BinaryWriter &stream, $qualified$ value) -> $encoded$
            {
                if (!enum_contains(value)) $unknown$
                $write$
                return {};
            }

            auto $serializer$::deserialize(BinaryReader &stream) -> $decoded$
            {
                auto v = $read$;
                if (!v) $read_failure$
                const auto value = enum_cast<$qualified$>(*v);
                if (!value) $unknown$
                return *value;
            }

            """,
            serializer=self.serializer,
            qualified=self.qualified,
            write=names.write("str", None, "enum_name(value)"),
            read=names.read("str", None),
            encoded=names.ENCODED,
            decoded=names.decoded(self.qualified),
            read_failure=names.unexpected("v.error()"),
            unknown=names.unexpected(names.UNKNOWN_VALUE),
        )
