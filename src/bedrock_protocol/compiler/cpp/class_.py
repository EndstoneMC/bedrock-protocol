"""`ClassGenerator` — one struct shape: its `struct { ... };` definition and
its `Serializer<T>` specialization (declaration in the header, out-of-line
bodies in the source). protoc analog: `compiler/cpp/cpp_message.{h,cc}`.

The serializer bodies iterate the struct's fields and delegate each to the
`FieldGenerator` built by `make_field_generator` — protoc's
`field_generators_.get(field).GenerateSerialize...` pattern.
"""

from __future__ import annotations

from bedrock_protocol.descriptor import Struct
from .field import FileContext, GenContext, cpp_type, make_field_generator
from .printer import Printer


class ClassGenerator:
    """One (possibly snapshot-narrowed) `Struct` → its C++ struct + serializer.

    `qualified` is the `Serializer<...>` target spelling (`Foo` when
    unversioned, `v1001::Foo` for a snapshot); `snapshot` drives the
    snapshot-qualified references inside the serializer bodies."""

    def __init__(
        self,
        struct: Struct,
        ctx: FileContext,
        *,
        snapshot: int | None = None,
        qualified: str | None = None,
    ) -> None:
        self._struct = struct
        self._ctx = ctx
        self._snapshot = snapshot
        self._qualified = qualified if qualified is not None else struct.name

    # --- type definition ----------------------------------------------------

    def generate_class_definition(self, p: Printer) -> None:
        """`struct Name { [static constexpr int Id;] fields... };`. Emitted
        inside the type's own namespace, so field types are unqualified."""
        rendered: list[tuple[str, str]] = []
        for f in self._struct.fields:
            (version,) = f.versions
            ctype = cpp_type(version.type, self._ctx) if version.type is not None else None
            if ctype is None:
                p.print(f"struct {self._struct.name} {{}};\n")
                return
            rendered.append((ctype, f.name))
        p.print(f"struct {self._struct.name} {{\n")
        p.indent()
        if self._struct.packet_id is not None:
            p.print(f"static constexpr int Id = {self._struct.packet_id};\n")
        for ctype, fname in rendered:
            p.print(f"{ctype} {fname}{{}};\n")
        p.outdent()
        p.print("};\n")

    # --- serializer ---------------------------------------------------------

    def generate_serializer_declaration(self, p: Printer) -> None:
        q = self._qualified
        p.print("template <>\n")
        p.print(f"struct Serializer<{q}> {{\n")
        p.indent()
        p.print(f"static void serialize(BinaryWriter &stream, const {q} &value);\n")
        p.print(f"static auto deserialize(BinaryReader &stream) -> std::expected<{q}, std::error_code>;\n")
        p.outdent()
        p.print("};\n")

    def generate_serializer_definition(self, p: Printer) -> None:
        q = self._qualified
        gc = GenContext(self._ctx, self._snapshot)

        p.print(f"void Serializer<{q}>::serialize(BinaryWriter &stream, const {q} &value)\n")
        with p.block():
            for f in self._struct.fields:
                (version,) = f.versions
                assert version.type is not None
                make_field_generator(version.type, gc).generate_serialize(p, f"value.{f.name}")
        p.print("\n")
        p.print(f"auto Serializer<{q}>::deserialize(BinaryReader &stream) -> std::expected<{q}, std::error_code>\n")
        with p.block():
            p.print(f"{q} out;\n")
            for f in self._struct.fields:
                (version,) = f.versions
                assert version.type is not None
                gen = make_field_generator(version.type, gc)
                with p.block():  # scope each field's read locals (v, present, len, tag, ...)
                    gen.generate_deserialize(p, f"out.{f.name}")
            p.print("return out;\n")
