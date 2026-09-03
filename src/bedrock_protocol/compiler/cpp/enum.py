"""`EnumGenerator` — one `enum class` plus, for a name-coded enum, its
`Serializer<Enum>` specialization. protoc analog: `compiler/cpp/cpp_enum.{h,cc}`.
"""

from __future__ import annotations

from collections.abc import Callable

from bedrock_protocol.descriptor import CompilerError, Enum, EnumValue

from .field import type_includes
from .helpers import INCLUDE_PREFIX, PRIMITIVE_TYPES
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
        self._reject_collisions()
        underlying = self._enum.sole_underlying
        p.add_includes(*type_includes(underlying))
        ctype = PRIMITIVE_TYPES[underlying.name]
        p.print(f"enum class {self._enum.name} : {ctype} {{\n")
        p.indent()
        cpp_names = {v.name: v.cpp_name for v in self._enum.values}
        for v in self._enum.values:
            # a negative member of an unsigned enum wraps; C++ needs that spelled out
            number = f"static_cast<{ctype}>({v.number})" if v.number < 0 and ctype.startswith("std::uint") else v.number
            p.print(f"{v.cpp_name} = {self._spelled(v, cpp_names, number)},\n")
        p.outdent()
        p.print("};\n")

    # --- reflection (magic_enum-like name <-> value tables) -----------------

    def generate_reflection(self, p: Printer, qualified: str, type_name: str | None = None) -> None:
        """The name table is lowercased for every enum, name-coded or not. It is the
        wire table for the ones that need one, and `enum_cast` folds its input, so a
        single spelling makes every name lookup case-insensitive by construction."""
        p.add_includes(f"<{INCLUDE_PREFIX}/enum.hpp>", "<array>", "<string_view>")
        values = self._enum.values
        n = len(values)
        p.print("template <>\n")
        p.print(f"inline constexpr std::array<{qualified}, {n}> values_v<{qualified}>{{{{\n")
        p.indent()
        for v in values:
            p.print(f"{qualified}::{v.cpp_name},\n")
        p.outdent()
        p.print("}};\n\n")
        p.print("template <>\n")
        p.print(f"inline constexpr std::array<std::string_view, {n}> names_v<{qualified}>{{{{\n")
        p.indent()
        for v in values:
            p.print(f'"{v.wire_name}",\n')
        p.outdent()
        p.print("}};\n\n")
        p.print("template <>\n")
        spelled = type_name if type_name is not None else self._enum.name
        p.print(f'inline constexpr std::string_view type_name_v<{qualified}>{{"{spelled}"}};\n')

    # --- serializer (name-coded: BDS's spelling, lowercased, on the wire) ---

    def generate_serializer_declaration(self, p: Printer) -> None:
        p.add_includes(
            f"<{INCLUDE_PREFIX}/serializer.hpp>", f"<{INCLUDE_PREFIX}/stream.hpp>", "<expected>", "<system_error>"
        )
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
            f"<{INCLUDE_PREFIX}/enum.hpp>",
            f"<{INCLUDE_PREFIX}/serializer.hpp>",
            f"<{INCLUDE_PREFIX}/stream.hpp>",
            "<expected>",
            "<string>",
            "<system_error>",
        )
        q = self._qualified
        p.print(f"void Serializer<{q}>::serialize(BinaryWriter &stream, {q} value)\n")
        with p.block():
            # A value with no name is unencodable, and the write path has no error to
            # return. Skipping the field would take the length prefix with it and leave
            # every later field one string out of step, which reads as a desync a long
            # way from its cause. The empty name keeps the stream aligned and no reader
            # accepts it, so the failure lands on the next deserialize.
            p.print("stream.write(enum_name(value));\n")
        p.print("\n")
        p.print(f"auto Serializer<{q}>::deserialize(BinaryReader &stream) -> std::expected<{q}, std::error_code>\n")
        with p.block():
            # BDS folds at bind time, not at lookup: it matches the lowercased name and
            # nothing else. The table is lowercased to match, and enum_cast folds its
            # input against it, so a peer sending BDS's binding casing still resolves --
            # and never onto a different member, which the check above guarantees.
            # enum_cast keys an unordered_map per enum on first use.
            p.print("auto v = stream.read<std::string>();\n")
            p.print("if (!v) return std::unexpected(v.error());\n")
            p.print(f"const auto value = enum_cast<{q}>(*v);\n")
            p.print("if (!value) return std::unexpected(std::make_error_code(std::errc::illegal_byte_sequence));\n")
            p.print("return *value;\n")

    @staticmethod
    def _spelled(v: EnumValue, cpp_names: dict[str, str], number: object) -> object:
        """The member's value as the schema spelled it. A member defined against a
        sibling keeps the arithmetic -- `Latest = NumValidVersions - 1` -- so the
        header restates what BDS derives instead of freezing today's number.
        Anything else is the resolved literal."""
        if v.derived is None:
            return number
        ref, offset = v.derived
        base = cpp_names[ref]
        if offset == 0:
            return base
        return f"{base} {'+' if offset > 0 else '-'} {abs(offset)}"

    def _reject_collisions(self) -> None:
        """Two members the derived spelling maps onto one name. In C++ that is a
        redefinition; on the wire the read keeps whichever came first without a word
        and `detail::name_index` drops the rest -- so both run for every enum, not
        only the name-coded ones whose table reaches the wire."""
        self._reject_clashes("C++ enumerator", lambda v: v.cpp_name)
        self._reject_clashes("wire name once folded", lambda v: v.wire_name)

    def _reject_clashes(self, what: str, key: Callable[[EnumValue], str]) -> None:
        by_key: dict[str, list[str]] = {}
        for v in self._enum.values:
            by_key.setdefault(key(v), []).append(v.name)
        clashes = {k: names for k, names in by_key.items() if len(set(names)) > 1}
        if clashes:
            spelled = "; ".join(f"{', '.join(names)} -> {k!r}" for k, names in sorted(clashes.items()))
            raise CompilerError(f"{self._qualified}: members share a {what} -- {spelled}")
