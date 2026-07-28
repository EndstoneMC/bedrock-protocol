"""`MessageGenerator` — one struct shape: its `struct { ... };` definition and
its `Serializer<T>` specialization (declaration in the header, out-of-line
bodies in the source). protoc analog: `compiler/cpp/cpp_message.{h,cc}`.

The serializer bodies iterate the struct's fields and delegate each to the
`FieldGenerator` its `FieldGeneratorMap` holds — protoc's
`field_generators_.get(field).GenerateSerialize...` pattern.
"""

from __future__ import annotations

from bedrock_protocol.descriptor import CondType, Enum, Field, Predicate, Struct

from .enum import EnumGenerator
from .field import FieldGeneratorMap, FileContext, cpp_type, render_predicate, type_includes
from .helpers import snapshot_namespace
from .printer import Printer


class MessageGenerator:
    """One (possibly snapshot-narrowed) `Struct` → its C++ struct + serializer.

    `qualified` is the `Serializer<...>` target spelling (`Foo` when
    unversioned, `v1001::Foo` for a snapshot); `snapshot` drives the
    snapshot-qualified references inside the serializer bodies.

    `nested_anchor` is the snapshot whose namespace holds the canonical
    definitions of this struct's nested types. When set, the body aliases them
    (`using ActionType = base::Owner::ActionType;`) instead of defining them
    again, so a nested type stays one C++ type across every snapshot of its
    owner."""

    def __init__(
        self,
        struct: Struct,
        ctx: FileContext,
        *,
        snapshot: int | None = None,
        qualified: str | None = None,
        nested_anchor: int | None = None,
    ) -> None:
        self._struct = struct
        self._ctx = ctx
        self._snapshot = snapshot
        self._qualified = qualified if qualified is not None else struct.name
        self._anchor = nested_anchor
        self._field_generators = FieldGeneratorMap(struct, ctx, snapshot)

    # --- type definition ----------------------------------------------------

    def generate_class_definition(self, p: Printer) -> None:
        """`struct Name { nested... [static constexpr int Id;] fields... };`.
        Emitted inside the type's own namespace, so field types are unqualified."""
        rendered: list[tuple[str, str]] = []
        for f in self._struct.fields:
            (version,) = f.versions
            ctype = cpp_type(version.type, self._ctx) if version.type is not None else None
            if ctype is None:
                p.print(f"struct {self._struct.name} {{}};\n")
                return
            p.add_includes(*type_includes(version.type))
            rendered.append((ctype, f.name))
        p.print(f"struct {self._struct.name} {{\n")
        p.indent()
        has_body = self._struct.packet_id is not None or bool(rendered)
        for i, inner in enumerate(self._struct.nested):
            self._generate_nested(p, inner)
            # Definitions stand apart; a run of `using` aliases reads as one block.
            if self._anchor is None and i + 1 < len(self._struct.nested):
                p.print("\n")
        if self._struct.nested and has_body:
            p.print("\n")
        if self._struct.packet_id is not None:
            p.print(f"static constexpr int Id = {self._struct.packet_id};\n")
        for ctype, fname in rendered:
            p.print(f"{ctype} {fname}{{}};\n")
        p.outdent()
        p.print("};\n")

    def _generate_nested(self, p: Printer, inner: Enum | Struct) -> None:
        if self._anchor is not None:
            ns = snapshot_namespace(self._anchor)
            p.print(f"using {inner.name} = {ns}::{self._struct.name}::{inner.name};\n")
        elif isinstance(inner, Enum):
            EnumGenerator(inner).generate_definition(p)
        else:
            MessageGenerator(inner, self._ctx, snapshot=self._snapshot).generate_class_definition(p)

    # --- serializer ---------------------------------------------------------

    def generate_serializer_declaration(self, p: Printer) -> None:
        p.add_includes("<bedrock/serializer.hpp>", "<bedrock/stream.hpp>", "<expected>", "<system_error>")
        q = self._qualified
        p.print("template <>\n")
        p.print(f"struct Serializer<{q}> {{\n")
        p.indent()
        p.print(f"static void serialize(BinaryWriter &stream, const {q} &value);\n")
        p.print(f"static auto deserialize(BinaryReader &stream) -> std::expected<{q}, std::error_code>;\n")
        p.outdent()
        p.print("};\n")

    def generate_serializer_definition(self, p: Printer) -> None:
        p.add_includes("<bedrock/serializer.hpp>", "<bedrock/stream.hpp>")
        q = self._qualified

        p.print(f"void Serializer<{q}>::serialize(BinaryWriter &stream, const {q} &value)\n")
        with p.block():
            for guard, group in self._groups():
                if guard is None:
                    (f,) = group
                    self._field_generators.get(f).generate_serialize(p, f"value.{f.name}")
                    continue
                with p.block(f"if ({self._condition(guard, 'value')})"):
                    for f in group:
                        self._field_generators.get(f).generate_serialize(p, f"value.{f.name}")
        p.print("\n")
        p.print(f"auto Serializer<{q}>::deserialize(BinaryReader &stream) -> std::expected<{q}, std::error_code>\n")
        with p.block():
            p.print(f"{q} out;\n")
            for guard, group in self._groups():
                if guard is None:
                    (f,) = group
                    with p.block():  # scope each field's read locals (v, present, len, tag, ...)
                        self._field_generators.get(f).generate_deserialize(p, f"out.{f.name}")
                    continue
                with p.block(f"if ({self._condition(guard, 'out')})"):
                    for f in group:
                        with p.block():
                            self._field_generators.get(f).generate_deserialize(p, f"out.{f.name}")
            p.print("return out;\n")

    # --- gated fields -------------------------------------------------------

    def _condition(self, guard: Predicate, base: str) -> str:
        return render_predicate(guard, base, self._ctx, self._snapshot)

    def _groups(self) -> list[tuple[Predicate | None, list[Field]]]:
        """The fields partitioned into emission groups. Fields hoisted out of one
        `with field(when=...)` block share a `CondType.group` and emit under a
        single `if`; every other field stands alone."""
        groups: list[tuple[Predicate | None, list[Field]]] = []
        open_group: int | None = None
        for f in self._struct.fields:
            (version,) = f.versions
            t = version.type
            if not isinstance(t, CondType):
                groups.append((None, [f]))
                open_group = None
            elif t.group is not None and t.group == open_group:
                groups[-1][1].append(f)
            else:
                groups.append((t.predicate, [f]))
                open_group = t.group
        return groups
