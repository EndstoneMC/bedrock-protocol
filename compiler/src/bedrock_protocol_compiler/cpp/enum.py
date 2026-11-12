from bedrock_protocol_compiler.cpp import names
from bedrock_protocol_compiler.cpp.field import primitive_includes
from bedrock_protocol_compiler.descriptor import Binary, Int, MemberRef
from bedrock_protocol_compiler.printer import Printer
from bedrock_protocol_compiler.schema import EnumShape, Schema


class EnumGenerator:
    def __init__(self, schema: Schema, shape: EnumShape) -> None:
        self.shape = shape
        self.qualified = names.qualified(schema, shape)
        self.underlying = "int" if shape.underlying.name == "int32" else names.PRIMITIVES[shape.underlying.name]
        self.name_coded = shape.family in schema.name_coded

    def includes(self) -> set[str]:
        includes = {names.runtime("enum"), "<array>", "<string_view>"}
        if self.shape.underlying.name != "int32":
            includes |= primitive_includes(self.shape.underlying)
        if self.name_coded:
            includes |= names.SERIALIZER_INCLUDES
        return includes

    def definition(self, p: Printer) -> None:
        cpp_names = {member.name: member.cpp_name for member in self.shape.members}
        p.emit("enum class $name$ : $underlying$ {", name=self.shape.family.name, underlying=self.underlying)
        with p.indent():
            for member in self.shape.members:
                match member.value:
                    case MemberRef(name=name):
                        spelled = cpp_names[name]
                    case Binary(left=MemberRef(name=name), right=Int(value=offset)):
                        spelled = f"{cpp_names[name]} - {offset}"
                    case Int(value=number) if number < 0 and self.underlying.startswith("std::uint"):
                        spelled = f"static_cast<{self.underlying}>({number})"
                    case Int(value=number):
                        spelled = str(number)
                    case _:
                        raise AssertionError(member.name)
                p.emit("$name$ = $value$,", name=member.cpp_name, value=spelled)
        p.emit("};")

    def reflection(self, p: Printer) -> None:
        if not self.shape.members:
            return
        members = sorted(self.shape.members, key=lambda member: not isinstance(member.value, MemberRef | Binary))
        tables = (
            ("values_v", self.qualified, [f"{self.qualified}::{member.cpp_name}" for member in members]),
            ("names_v", "std::string_view", [f'"{member.wire_name}"' for member in members]),
            ("schema_names_v", "std::string_view", [f'"{member.name}"' for member in members]),
        )
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
            name=names.bare(self.shape.family),
        )

    def serializer_declaration(self, p: Printer) -> None:
        if not self.name_coded:
            return
        p.emit(
            """
            template <>
            struct Serializer<$qualified$> {
                static void serialize(BinaryWriter &stream, $qualified$ value);
                static auto deserialize(BinaryReader &stream) -> $decoded$;
            };

            """,
            qualified=self.qualified,
            decoded=names.decoded(self.qualified),
        )

    def serializer_body(self, p: Printer) -> None:
        if not self.name_coded:
            return
        p.emit(
            """
            void Serializer<$qualified$>::serialize(BinaryWriter &stream, $qualified$ value)
            {
                $write$
            }

            auto Serializer<$qualified$>::deserialize(BinaryReader &stream) -> $decoded$
            {
                auto v = $read$;
                if (!v) $read_failure$
                const auto value = enum_cast<$qualified$>(*v);
                if (!value) $unknown$
                return *value;
            }

            """,
            qualified=self.qualified,
            write=names.write("str", None, "enum_name(value)"),
            read=names.read("str", None),
            decoded=names.decoded(self.qualified),
            read_failure=names.unexpected("v.error()"),
            unknown=names.unexpected(names.UNKNOWN_VALUE),
        )
