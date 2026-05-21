"""`SerializerGenerator` — emits `Serializer<T>` specializations.

Three flavors: struct serializers (one per concrete struct shape — a fresh
snapshot view or an unversioned struct), name-coded enum serializers, and
`type` alias serializers for `std::variant`-shaped aliases that need
their own codec at namespace scope.

The two walkers `_emit_write` and `_emit_read` recurse through a
`FieldType` and emit the C++ that pushes / pulls each node onto / from
the wire. protoc analog: blended pieces of `cpp_message.cc` and
`cpp_field.cc`.
"""

from __future__ import annotations

from ...descriptor import (
    VARINT_PRIMITIVES,
    BitsetType,
    CondType,
    Enum,
    EnumType,
    Field,
    FieldType,
    MappingType,
    OptionalType,
    Predicate,
    PrimitiveType,
    RepeatedType,
    Struct,
    StructType,
    TypeAlias,
    VariantType,
)
from .field import FileContext, cpp_type, qualified_at, render_predicate
from .names import PRIMITIVE_TYPES, camel, snapshot_namespace
from .printer import Printer


class SerializerGenerator:
    """Per-file generator for `Serializer<T>` specializations."""

    def __init__(self, ctx: FileContext) -> None:
        self._ctx = ctx
        # Walker state set per emit_* call.
        self._snapshot: int | None = None
        self._owner_qualified = ""
        self._nested_enums: frozenset[str] = frozenset()
        self._loop_depth = 0

    # --- public emitters ----------------------------------------------------

    def emit_for_struct(
        self,
        p: Printer,
        struct: Struct,
        view: Struct | None,
        snapshot: int | None = None,
    ) -> bool:
        """Emit the `Serializer<X>` specialization for one struct shape.
        Returns False if the struct couldn't be serialized (unresolved field
        type); the caller should skip it."""
        if view is None:
            fields = struct.fields
            qualified = struct.name
        else:
            assert snapshot is not None
            fields = view.fields
            qualified = f"{snapshot_namespace(snapshot)}::{struct.name}"
        typed: list[tuple[Field, FieldType]] = []
        for f in fields:
            t = f.type_single
            if t is None:
                return False
            typed.append((f, t))
        self._snapshot = snapshot
        self._owner_qualified = qualified
        self._nested_enums = frozenset(e.name for e in struct.nested_enums)
        self._loop_depth = 0
        groups = _field_groups(typed)
        param = f"const {qualified} &value"

        self._emit_template_open(p, qualified, param)
        with p.indented(2):
            self._emit_struct_serialize(p, groups)
        p("    }")
        p()
        self._emit_template_deserialize_open(p, qualified)
        with p.indented(2):
            p(f"{qualified} out;")
            self._emit_struct_deserialize(p, groups)
            p("return out;")
        p("    }")
        p("};")
        return True

    def emit_for_variant_alias(self, p: Printer, alias: TypeAlias) -> None:
        """Emit `Serializer<Alias>` for a `type Alias = T1 | T2` declaration."""
        self._snapshot = None
        self._owner_qualified = alias.name
        self._nested_enums = frozenset()
        self._loop_depth = 0
        qualified = alias.name
        param = f"const {qualified} &value"

        self._emit_template_open(p, qualified, param)
        with p.indented(2):
            self._emit_write(p, alias.target, "value")
        p("    }")
        p()
        self._emit_template_deserialize_open(p, qualified)
        with p.indented(2):
            p(f"{qualified} out;")
            self._emit_read(p, alias.target, "out")
            p("return out;")
        p("    }")
        p("};")

    def emit_for_enum(self, p: Printer, enum: Enum, snapshot: int | None) -> None:
        """Emit `Serializer<Enum>` for a name-coded enum (string on the wire)."""
        if snapshot is None:
            qualified = enum.name
        else:
            qualified = f"{snapshot_namespace(snapshot)}::{enum.name}"
        param = f"{qualified} value"
        p("template <>")
        p(f"struct Serializer<{qualified}> {{")
        p(f"    static void serialize(BinaryStream &stream, {param})")
        p("    {")
        with p.indented(2):
            p(f"using E = {qualified};")
            for v in enum.values:
                p(
                    f"if (value == E::{camel(v.name)}) {{ "
                    f'stream.write(std::string_view{{"{v.wire_name}"}}); return; }}'
                )
        p("    }")
        p()
        self._emit_template_deserialize_open(p, qualified)
        with p.indented(2):
            p(f"using E = {qualified};")
            p("auto v = stream.read<std::string>();")
            p("if (!v) return make_unexpected(v.error());")
            for v in enum.values:
                p(f'if (*v == "{v.wire_name}") return E::{camel(v.name)};')
            p(
                "return make_unexpected("
                "std::make_error_code(std::errc::illegal_byte_sequence));"
            )
        p("    }")
        p("};")

    # --- struct serializer assembly ----------------------------------------

    def _emit_struct_serialize(
        self,
        p: Printer,
        groups: list[tuple[Predicate | None, list[tuple[Field, FieldType]]]],
    ) -> None:
        for guard, group in groups:
            if guard is None:
                ((f, t),) = group
                self._emit_write(p, t, f"value.{f.name}")
                continue
            expr = render_predicate(
                guard, "value", self._ctx, self._owner_qualified,
                self._nested_enums, self._snapshot,
            )
            p(f"if ({expr}) {{")
            with p.indented():
                for f, t in group:
                    assert isinstance(t, CondType)
                    self._emit_write(p, t.inner, f"value.{f.name}")
            p("}")

    def _emit_struct_deserialize(
        self,
        p: Printer,
        groups: list[tuple[Predicate | None, list[tuple[Field, FieldType]]]],
    ) -> None:
        for guard, group in groups:
            if guard is None:
                ((f, t),) = group
                p("{")
                with p.indented():
                    self._emit_read(p, t, f"out.{f.name}")
                p("}")
                continue
            expr = render_predicate(
                guard, "out", self._ctx, self._owner_qualified,
                self._nested_enums, self._snapshot,
            )
            p(f"if ({expr}) {{")
            with p.indented():
                for f, t in group:
                    assert isinstance(t, CondType)
                    p("{")
                    with p.indented():
                        self._emit_read(p, t.inner, f"out.{f.name}")
                    p("}")
            p("}")

    # --- write walker ------------------------------------------------------

    def _emit_write(self, p: Printer, t: FieldType, expr: str) -> None:
        if isinstance(t, PrimitiveType):
            p(_primitive_write(t, expr))
        elif isinstance(t, StructType):
            p(f"Serializer<{self._type_at(t.name)}>::serialize(stream, {expr});")
        elif isinstance(t, EnumType):
            if t.scalar is None:
                p(f"Serializer<{self._type_at(t.name)}>::serialize(stream, {expr});")
            else:
                p(_primitive_write(t.scalar, expr))
        elif isinstance(t, OptionalType):
            if t.discriminator:
                p(
                    f"stream.writeVarInt<std::uint32_t>"
                    f"({expr}.has_value() ? {t.present_tag}u : {1 - t.present_tag}u);"
                )
            else:
                p(f"stream.write<bool>({expr}.has_value());")
            p(f"if ({expr}.has_value()) {{")
            with p.indented():
                self._emit_write(p, t.inner, f"*{expr}")
            p("}")
        elif isinstance(t, RepeatedType):
            depth = self._loop_depth
            self._loop_depth += 1
            if t.prefix is not None:
                p(_primitive_write(t.prefix, f"{expr}.size()"))
            p(f"for (const auto &e{depth} : {expr}) {{")
            with p.indented():
                self._emit_write(p, t.inner, f"e{depth}")
            p("}")
            self._loop_depth -= 1
        elif isinstance(t, MappingType):
            depth = self._loop_depth
            self._loop_depth += 1
            p(_primitive_write(t.prefix, f"{expr}.size()"))
            p(f"for (const auto &[k{depth}, v{depth}] : {expr}) {{")
            with p.indented():
                self._emit_write(p, t.key, f"k{depth}")
                self._emit_write(p, t.value, f"v{depth}")
            p("}")
            self._loop_depth -= 1
        elif isinstance(t, VariantType):
            p(f"{_primitive_write(t.discriminator, f'({expr}).index()')}")
            p(f"switch (({expr}).index()) {{")
            with p.indented():
                for index, case in enumerate(t.cases):
                    p(f"case {index}: {{")
                    with p.indented():
                        if case is not None:
                            self._emit_write(
                                p, case, f"std::get<{index}>({expr})"
                            )
                        p("break;")
                    p("}")
            p("}")
        elif isinstance(t, BitsetType):
            p(f"Serializer<std::bitset<{t.size}>>::serialize(stream, {expr});")
        elif isinstance(t, CondType):
            self._emit_write(p, t.inner, expr)

    # --- read walker -------------------------------------------------------

    def _emit_read(self, p: Printer, t: FieldType, target: str) -> None:
        if isinstance(t, PrimitiveType):
            _primitive_read(p, t)
            if t.name in ("str", "bytes") and t.alias is None:
                p(f"{target} = *v;")
            else:
                cast = cpp_type(t, self._ctx, self._nested_enums)
                p(f"{target} = static_cast<{cast}>(*v);")
        elif isinstance(t, StructType):
            p(f"auto v = Serializer<{self._type_at(t.name)}>::deserialize(stream);")
            p("if (!v) return make_unexpected(v.error());")
            p(f"{target} = *v;")
        elif isinstance(t, EnumType):
            if t.scalar is None:
                p(f"auto v = Serializer<{self._type_at(t.name)}>::deserialize(stream);")
                p("if (!v) return make_unexpected(v.error());")
                p(f"{target} = *v;")
            else:
                _primitive_read(p, t.scalar)
                p(f"{target} = static_cast<{self._type_at(t.name)}>(*v);")
        elif isinstance(t, OptionalType):
            holder = "tag" if t.discriminator else "present"
            verb = "readVarInt<std::uint32_t>" if t.discriminator else "read<bool>"
            guard = f"*tag == {t.present_tag}" if t.discriminator else "*present"
            p(f"auto {holder} = stream.{verb}();")
            p(f"if (!{holder}) return make_unexpected({holder}.error());")
            p(f"if ({guard}) {{")
            with p.indented():
                self._emit_read(p, t.inner, target)
            p("}")
        elif isinstance(t, RepeatedType):
            depth = self._loop_depth
            self._loop_depth += 1
            if t.prefix is not None:
                u = PRIMITIVE_TYPES[t.prefix.name]
                verb = (
                    f"readVarInt<{u}>"
                    if t.prefix.name in VARINT_PRIMITIVES
                    else f"read<{u}>"
                )
                p(f"auto len{depth} = stream.{verb}();")
                p(f"if (!len{depth}) return make_unexpected(len{depth}.error());")
                p(f"{target}.clear();")
                p(
                    f"for (auto rep{depth} = *len{depth}; "
                    f"rep{depth} > 0; --rep{depth}) {{"
                )
                with p.indented():
                    p(f"{target}.emplace_back();")
                    self._emit_read(p, t.inner, f"{target}.back()")
                p("}")
            else:
                p(
                    f"for (std::size_t i{depth} = 0; "
                    f"i{depth} < {t.count}; ++i{depth}) {{"
                )
                with p.indented():
                    self._emit_read(p, t.inner, f"{target}[i{depth}]")
                p("}")
            self._loop_depth -= 1
        elif isinstance(t, MappingType):
            depth = self._loop_depth
            self._loop_depth += 1
            u = PRIMITIVE_TYPES[t.prefix.name]
            verb = (
                f"readVarInt<{u}>"
                if t.prefix.name in VARINT_PRIMITIVES
                else f"read<{u}>"
            )
            p(f"auto len{depth} = stream.{verb}();")
            p(f"if (!len{depth}) return make_unexpected(len{depth}.error());")
            p(f"{target}.clear();")
            holder = f"std::remove_reference_t<decltype({target})>"
            p(
                f"for (auto rep{depth} = *len{depth}; "
                f"rep{depth} > 0; --rep{depth}) {{"
            )
            with p.indented():
                p(f"{holder}::key_type k{depth}{{}};")
                p("{")
                with p.indented():
                    self._emit_read(p, t.key, f"k{depth}")
                p("}")
                p(f"{holder}::mapped_type v{depth}{{}};")
                p("{")
                with p.indented():
                    self._emit_read(p, t.value, f"v{depth}")
                p("}")
                p(f"{target}.emplace(k{depth}, v{depth});")
            p("}")
            self._loop_depth -= 1
        elif isinstance(t, VariantType):
            depth = self._loop_depth
            self._loop_depth += 1
            vartype = cpp_type(t, self._ctx, self._nested_enums)
            assert vartype is not None
            d = t.discriminator
            u = PRIMITIVE_TYPES[d.name]
            verb = (
                f"readVarInt<{u}>"
                if d.name in VARINT_PRIMITIVES
                else f"read<{u}>"
            )
            p(f"auto tag{depth} = stream.{verb}();")
            p(f"if (!tag{depth}) return make_unexpected(tag{depth}.error());")
            p(f"{vartype} var{depth}{{}};")
            p(f"switch (*tag{depth}) {{")
            with p.indented():
                for index, case in enumerate(t.cases):
                    p(f"case {index}: {{")
                    with p.indented():
                        p(
                            f"std::variant_alternative_t<{index}, {vartype}> "
                            f"alt{depth}{{}};"
                        )
                        if case is not None:
                            p("{")
                            with p.indented():
                                self._emit_read(p, case, f"alt{depth}")
                            p("}")
                        p(f"var{depth}.emplace<{index}>(alt{depth});")
                        p("break;")
                    p("}")
                p("default: {")
                with p.indented():
                    p(
                        "return make_unexpected(std::make_error_code("
                        "std::errc::illegal_byte_sequence));"
                    )
                p("}")
            p("}")
            p(f"{target} = var{depth};")
            self._loop_depth -= 1
        elif isinstance(t, BitsetType):
            p(f"auto v = Serializer<std::bitset<{t.size}>>::deserialize(stream);")
            p("if (!v) return make_unexpected(v.error());")
            p(f"{target} = *v;")
        elif isinstance(t, CondType):
            self._emit_read(p, t.inner, target)

    # --- helpers ------------------------------------------------------------

    def _emit_template_open(self, p: Printer, qualified: str, param: str) -> None:
        p("template <>")
        p(f"struct Serializer<{qualified}> {{")
        p(f"    static void serialize(BinaryStream &stream, {param})")
        p("    {")

    def _emit_template_deserialize_open(self, p: Printer, qualified: str) -> None:
        p(
            f"    static auto deserialize(BinaryReader &stream) -> "
            f"std::expected<{qualified}, std::error_code>"
        )
        p("    {")

    def _type_at(self, name: str) -> str:
        return qualified_at(
            name, self._ctx, self._owner_qualified, self._nested_enums,
            self._snapshot,
        )


# --- module-free helpers --------------------------------------------------------


def _field_groups(
    typed: list[tuple[Field, FieldType]],
) -> list[tuple[Predicate | None, list[tuple[Field, FieldType]]]]:
    """Partition a struct's fields into emission groups. Fields from one
    `with field(when=...)` block (sharing a `CondType.group`) form one
    group emitted under a shared `if`; everything else stands alone."""
    groups: list[tuple[Predicate | None, list[tuple[Field, FieldType]]]] = []
    open_group: int | None = None
    for f, t in typed:
        if (
            isinstance(t, CondType)
            and t.group is not None
            and t.group == open_group
        ):
            groups[-1][1].append((f, t))
            continue
        if isinstance(t, CondType):
            groups.append((t.predicate, [(f, t)]))
            open_group = t.group
        else:
            groups.append((None, [(f, t)]))
            open_group = None
    return groups


def _primitive_write(p: PrimitiveType, expr: str) -> str:
    if p.trailing:
        return f"stream.writeRawBytes({expr});"
    if p.name in ("str", "bytes"):
        return f"stream.write({expr});"
    u = PRIMITIVE_TYPES[p.name]
    if p.name in VARINT_PRIMITIVES:
        return f"stream.writeVarInt<{u}>({expr});"
    if p.big_endian:
        return f"stream.write<{u}, std::endian::big>({expr});"
    return f"stream.write<{u}>({expr});"


def _primitive_read(out: Printer, p: PrimitiveType) -> None:
    if p.trailing:
        out("auto v = stream.readRemaining();")
    elif p.name in ("str", "bytes"):
        out("auto v = stream.read<std::string>();")
    else:
        u = PRIMITIVE_TYPES[p.name]
        if p.name in VARINT_PRIMITIVES:
            out(f"auto v = stream.readVarInt<{u}>();")
        elif p.big_endian:
            out(f"auto v = stream.read<{u}, std::endian::big>();")
        else:
            out(f"auto v = stream.read<{u}>();")
    out("if (!v) return make_unexpected(v.error());")
