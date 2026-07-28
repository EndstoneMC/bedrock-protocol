"""`EnumGenerator` — one `enum class` plus, for a name-coded enum, its
`Serializer<Enum>` specialization. protoc analog: `compiler/cpp/cpp_enum.{h,cc}`.
"""

from __future__ import annotations

from bedrock_protocol.descriptor import Enum

from .field import type_includes
from .helpers import PRIMITIVE_TYPES
from .printer import Printer


class EnumGenerator:
    """One `Enum` descriptor → its C++ definition and, for a name-coded enum,
    its `Serializer`. `qualified` is the spelling used outside the enum's own
    scope -- `v1001::Owner::ActionType` for a nested enum, the bare name
    otherwise; the definition itself always emits unqualified."""

    def __init__(self, enum: Enum, qualified: str | None = None) -> None:
        self._enum = enum
        self._qualified = qualified if qualified is not None else enum.name

    # --- type definition ----------------------------------------------------

    def generate_definition(self, p: Printer) -> None:
        underlying = self._enum.underlying
        p.add_includes(*type_includes(underlying))
        ctype = "int" if underlying is None else PRIMITIVE_TYPES[underlying.name]
        p.print(f"enum class {self._enum.name} : {ctype} {{\n")
        p.indent()
        for v in self._enum.values:
            # a negative member of an unsigned enum wraps; C++ needs that spelled out
            number = f"static_cast<{ctype}>({v.number})" if v.number < 0 and ctype.startswith("std::uint") else v.number
            p.print(f"{v.name} = {number},\n")
        p.outdent()
        p.print("};\n")

    # --- reflection (magic_enum-like name <-> value tables) -----------------

    def generate_reflection(self, p: Printer, qualified: str, type_name: str | None = None) -> None:
        p.add_includes("<bedrock/enum.hpp>", "<array>", "<string_view>")
        values = self._enum.values
        n = len(values)
        p.print("template <>\n")
        p.print(f"inline constexpr std::array<{qualified}, {n}> values_v<{qualified}>{{{{\n")
        p.indent()
        for v in values:
            p.print(f"{qualified}::{v.name},\n")
        p.outdent()
        p.print("}};\n\n")
        p.print("template <>\n")
        p.print(f"inline constexpr std::array<std::string_view, {n}> names_v<{qualified}>{{{{\n")
        p.indent()
        for v in values:
            p.print(f'"{v.name}",\n')
        p.outdent()
        p.print("}};\n\n")
        p.print("template <>\n")
        spelled = type_name if type_name is not None else self._enum.name
        p.print(f'inline constexpr std::string_view type_name_v<{qualified}>{{"{spelled}"}};\n')

    # --- serializer (name-coded: verbatim member name on the wire) ----------

    def generate_serializer_declaration(self, p: Printer) -> None:
        p.add_includes("<bedrock/serializer.hpp>", "<bedrock/stream.hpp>", "<expected>", "<system_error>")
        q = self._qualified
        p.print("template <>\n")
        p.print(f"struct Serializer<{q}> {{\n")
        p.indent()
        p.print(f"static void serialize(BinaryWriter &stream, {q} value);\n")
        p.print(f"static auto deserialize(BinaryReader &stream) -> std::expected<{q}, std::error_code>;\n")
        p.outdent()
        p.print("};\n")

    def generate_serializer_definition(self, p: Printer) -> None:
        p.add_includes(
            "<bedrock/serializer.hpp>",
            "<bedrock/stream.hpp>",
            "<expected>",
            "<system_error>",
            "<cctype>",
            "<string>",
            "<string_view>",
            "<unordered_map>",
        )
        q = self._qualified
        p.print(f"void Serializer<{q}>::serialize(BinaryWriter &stream, {q} value)\n")
        with p.block():
            p.print(f"using E = {q};\n")
            p.print("static const std::unordered_map<E, std::string_view> names{\n")
            p.indent()
            for v in self._enum.values:
                p.print(f'{{E::{v.name}, "{v.wire_name}"}},\n')
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
                p.print(f'{{"{v.wire_name.lower()}", E::{v.name}}},\n')
            p.outdent()
            p.print("};\n")
            p.print("auto v = stream.read<std::string>();\n")
            p.print("if (!v) return std::unexpected(v.error());\n")
            p.print("for (auto &c : *v) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));\n")
            p.print("auto it = values.find(*v);\n")
            p.print(
                "if (it == values.end()) "
                "return std::unexpected(std::make_error_code(std::errc::illegal_byte_sequence));\n"
            )
            p.print("return it->second;\n")
