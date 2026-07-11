"""`EnumGenerator` — one `enum class` plus, for a name-coded enum, its
`Serializer<Enum>` specialization. protoc analog: `compiler/cpp/cpp_enum.{h,cc}`.
"""

from __future__ import annotations

from bedrock_protocol.descriptor import Enum
from .names import camel
from .printer import Printer


class EnumGenerator:
    def __init__(self, enum: Enum) -> None:
        self._enum = enum

    # --- type definition ----------------------------------------------------

    def generate_definition(self, p: Printer) -> None:
        p.print(f"enum class {self._enum.name} : int {{\n")
        p.indent()
        for v in self._enum.values:
            p.print(f"{camel(v.name)} = {v.number},\n")
        p.outdent()
        p.print("};\n")

    # --- serializer (name-coded: verbatim member name on the wire) ----------

    def generate_serializer_declaration(self, p: Printer) -> None:
        q = self._enum.name
        p.print("template <>\n")
        p.print(f"struct Serializer<{q}> {{\n")
        p.indent()
        p.print(f"static void serialize(BinaryWriter &stream, {q} value);\n")
        p.print(f"static auto deserialize(BinaryReader &stream) -> std::expected<{q}, std::error_code>;\n")
        p.outdent()
        p.print("};\n")

    def generate_serializer_definition(self, p: Printer) -> None:
        q = self._enum.name
        p.print(f"void Serializer<{q}>::serialize(BinaryWriter &stream, {q} value)\n")
        with p.block():
            p.print(f"using E = {q};\n")
            p.print("static const std::unordered_map<E, std::string_view> names{\n")
            p.indent()
            for v in self._enum.values:
                p.print(f'{{E::{camel(v.name)}, "{v.wire_name}"}},\n')
            p.outdent()
            p.print("};\n")
            p.print("auto it = names.find(value);\n")
            p.print("if (it != names.end()) stream.write(it->second);\n")
        p.print("\n")
        p.print(f"auto Serializer<{q}>::deserialize(BinaryReader &stream) -> std::expected<{q}, std::error_code>\n")
        with p.block():
            p.print(f"using E = {q};\n")
            # BDS lowercases the incoming string before the enum lookup, so the
            # read is case-insensitive; the keys are lowercased to match.
            p.print("static const std::unordered_map<std::string_view, E> values{\n")
            p.indent()
            for v in self._enum.values:
                p.print(f'{{"{v.wire_name.lower()}", E::{camel(v.name)}}},\n')
            p.outdent()
            p.print("};\n")
            p.print("auto v = stream.read<std::string>();\n")
            p.print("if (!v) return make_unexpected(v.error());\n")
            p.print("for (auto &c : *v) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));\n")
            p.print("auto it = values.find(*v);\n")
            p.print("if (it == values.end()) return make_unexpected(std::make_error_code(std::errc::illegal_byte_sequence));\n")
            p.print("return it->second;\n")
