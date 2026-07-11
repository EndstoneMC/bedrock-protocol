"""`FileGenerator` — assembles one C++ header/source pair end to end.

protoc analog: `compiler/cpp/cpp_file.{h,cc}`. Routes each section through a
`Printer`, delegating type definitions and serializers to `EnumGenerator` /
`ClassGenerator` and the `FieldGenerator` codec.

The `.hpp` holds type definitions, the DSL-owned `ProtocolVersion` `_<V>`
selector, and declaration-only `Serializer<T>` specializations; the `.cpp`
holds the out-of-line serializer bodies, compiled once into the static lib.
"""

from __future__ import annotations

from bedrock_protocol.descriptor import (
    Enum,
    EnumType,
    FieldType,
    OptionalType,
    PrimitiveType,
    RepeatedType,
    ResolvedFile,
    Struct,
    VariantType,
)
from .enum import EnumGenerator
from .field import FileContext, GenContext, cpp_type, make_field_generator
from .class_ import ClassGenerator
from .names import PRIMITIVE_TYPES, camel, requires_clause, snapshot_namespace
from .printer import Printer


class FileGenerator:
    def __init__(self, resolved: ResolvedFile) -> None:
        self._resolved = resolved
        self._file = resolved.file
        self._file_set = resolved.file_set
        known = frozenset(
            name
            for f in resolved.file_set.files.values()
            for name in (
                *(e.name for e in f.enums),
                *(s.name for s in f.structs),
                *(a.name for a in f.primitive_aliases),
                *(a.name for a in f.type_aliases),
            )
        )
        self._ctx = FileContext(
            resolved=resolved,
            known=known,
            string_coded_enums=_string_coded_enums(resolved),
        )

    # --- public driver ------------------------------------------------------

    def render_header(self, latest_version: int) -> str:
        p = Printer()
        p.print("#pragma once\n\n")
        self._emit_includes(p)
        self._emit_version_include(p)
        p.print("\n")
        self._emit_namespace_open(p)
        self._emit_primitive_aliases(p)
        self._emit_unversioned(p)
        self._emit_type_aliases(p)
        self._emit_versioned_namespaces(p)
        self._emit_traits(p)
        self._emit_serializers(p, mode="decl")
        self._emit_latest_aliases(p, latest_version)
        self._emit_namespace_close(p)
        return p.text

    def render_source(self) -> str:
        p = Printer()
        p.print(f'#include "{self._file.stem}.hpp"\n\n')
        self._emit_namespace_open(p)
        self._emit_serializers(p, mode="def")
        self._emit_namespace_close(p)
        return p.text

    # --- includes -----------------------------------------------------------

    def _emit_includes(self, p: Printer) -> None:
        """Emit exactly the headers the generated code uses, as a sorted set:
        stdlib first, then the bedrock codec headers."""
        stdlib = self._stdlib_includes()
        project: set[str] = set()
        if self._has_serializers():
            stdlib.add("<system_error>")
            project |= {"<bedrock/expected.hpp>", "<bedrock/serializer.hpp>", "<bedrock/stream.hpp>"}
        for inc in sorted(stdlib):
            p.print(f"#include {inc}\n")
        if project:
            p.print("\n")
            for inc in sorted(project):
                p.print(f"#include {inc}\n")

    def _stdlib_includes(self) -> set[str]:
        """The stdlib headers demanded by the file's types: `<vector>` only when
        a `std::vector` is generated, `<optional>` only for a `std::optional`,
        and so on."""
        out: set[str] = set()

        def walk(t: FieldType | None) -> None:
            if isinstance(t, PrimitiveType):
                if t.name in ("str", "bytes"):
                    out.add("<string>")
                elif PRIMITIVE_TYPES[t.name].startswith("std::"):
                    out.add("<cstdint>")
            elif isinstance(t, OptionalType):
                out.add("<optional>")
                walk(t.inner)
            elif isinstance(t, RepeatedType):
                out.add("<vector>")
                walk(t.prefix)
                walk(t.inner)
            elif isinstance(t, VariantType):
                out.add("<variant>")
                walk(t.discriminator)
                for c in t.cases:
                    walk(c)

        for s in self._file.structs:
            for f in s.fields:
                for v in f.versions:
                    walk(v.type)
        for a in self._file.type_aliases:
            walk(a.target)
        for a in self._file.primitive_aliases:
            if PRIMITIVE_TYPES[a.primitive].startswith("std::"):
                out.add("<cstdint>")
        if self._ctx.string_coded_enums:
            # name-coded enum serializer: unordered_map<E, string_view> + tolower.
            out |= {"<cctype>", "<string>", "<string_view>", "<unordered_map>"}
        return out

    def _emit_version_include(self, p: Printer) -> None:
        """A file with versioned types spells the `_<ProtocolVersion V>`
        selector, so pull in the generated version header."""
        if not self._has_namespaces():
            return
        for name, f in self._file_set.files.items():
            if f is self._file:
                continue
            if any(e.name == "ProtocolVersion" for e in f.enums):
                p.print(f'\n#include "{name.replace(".", "/")}.hpp"\n')
                return

    # --- namespace ----------------------------------------------------------

    def _emit_namespace_open(self, p: Printer) -> None:
        if self._file.package:
            p.print(f"namespace {self._file.package.replace('.', '::')} {{\n\n")

    def _emit_namespace_close(self, p: Printer) -> None:
        if self._file.package:
            p.print(f"\n}}  // namespace {self._file.package.replace('.', '::')}\n")

    # --- type declarations --------------------------------------------------

    def _emit_primitive_aliases(self, p: Printer) -> None:
        for a in self._file.primitive_aliases:
            p.print(f"enum {a.name} : {PRIMITIVE_TYPES[a.primitive]} {{}};\n")
        if self._file.primitive_aliases:
            p.print("\n")

    def _emit_unversioned(self, p: Printer) -> None:
        by_name = self._by_name()
        for name in self._unversioned_names():
            self._emit_definition(p, by_name[name])
            p.print("\n")

    def _emit_type_aliases(self, p: Printer) -> None:
        for a in self._file.type_aliases:
            ctype = cpp_type(a.target, self._ctx)
            assert ctype is not None
            p.print(f"using {a.name} = {ctype};\n")
        if self._file.type_aliases:
            p.print("\n")

    def _emit_versioned_namespaces(self, p: Printer) -> None:
        for snap in self._resolved.snapshots:
            if not self._snapshot_has_entries(snap):
                continue
            ns = snapshot_namespace(snap)
            p.print(f"namespace {ns} {{\n\n")
            for name in self._resolved.declaration_order:
                if not self._resolved.is_versioned(name):
                    continue
                view = self._resolved.present_at(name, snap)
                if view is None:
                    continue
                if view.is_fresh:
                    self._emit_definition(p, view.enum or view.struct)
                else:
                    p.print(f"using {name} = {snapshot_namespace(view.concrete)}::{name};\n")
                p.print("\n")
            p.print(f"}}  // namespace {ns}\n\n")

    def _emit_definition(self, p: Printer, t: Enum | Struct | None) -> None:
        if isinstance(t, Enum):
            EnumGenerator(t).generate_definition(p)
        elif isinstance(t, Struct):
            ClassGenerator(t, self._ctx).generate_class_definition(p)

    # --- versioning traits + selector --------------------------------------

    def _emit_traits(self, p: Printer) -> None:
        if not self._has_namespaces():
            return
        p.print("namespace detail {\n")
        by_name = self._by_name()
        for name in self._versioned_names():
            fresh = self._resolved.fresh_snapshots(name)
            p.print("\n")
            p.print("template <int V>\n")
            p.print(f"struct {name}_;\n")
            for j, s in enumerate(fresh):
                hi = fresh[j + 1].lo if j + 1 < len(fresh) else getattr(by_name.get(name), "until", None)
                p.print("\n")
                p.print(f"template <int V> requires ({requires_clause(s.lo, hi)})\n")
                p.print(f"struct {name}_<V> {{ using type = {snapshot_namespace(s.lo)}::{name}; }};\n")
        p.print("\n}  // namespace detail\n\n")
        venum = self._version_enum()
        vparam = venum.name if venum is not None else "int"
        varg = "static_cast<int>(V)" if venum is not None else "V"
        for name in self._versioned_names():
            p.print(f"template <{vparam} V> using {name}_ = typename detail::{name}_<{varg}>::type;\n")
        p.print("\n")

    def _emit_latest_aliases(self, p: Printer, latest_version: int) -> None:
        names = self._versioned_names()
        if not names:
            return
        by_name = self._by_name()
        venum = self._version_enum()
        latest_arg = str(latest_version)
        if venum is not None:
            member = next((camel(v.name) for v in venum.values if v.number == latest_version), None)
            if member is not None:
                latest_arg = f"{venum.name}::{member}"
        for name in names:
            until = getattr(by_name.get(name), "until", None)
            if until is not None and latest_version >= until:
                continue
            p.print(f"using {name} = {name}_<{latest_arg}>;\n")

    # --- serializers --------------------------------------------------------

    def _emit_serializers(self, p: Printer, mode: str) -> None:
        by_name = self._by_name()
        for name in self._resolved.declaration_order:
            t = by_name[name]
            if isinstance(t, Enum):
                if name in self._ctx.string_coded_enums:
                    p.print("\n")
                    self._emit_enum_serializer(p, t, mode)
                continue
            if self._resolved.is_versioned(name):
                for s in self._resolved.fresh_snapshots(name):
                    assert s.struct is not None
                    qualified = f"{snapshot_namespace(s.lo)}::{name}"
                    p.print("\n")
                    self._emit_struct_serializer(p, s.struct, s.lo, qualified, mode)
            else:
                p.print("\n")
                self._emit_struct_serializer(p, t, None, name, mode)
        for a in self._file.type_aliases:
            if isinstance(a.target, VariantType):
                p.print("\n")
                self._emit_variant_alias_serializer(p, a.name, a.target, mode)

    def _emit_enum_serializer(self, p: Printer, enum: Enum, mode: str) -> None:
        gen = EnumGenerator(enum)
        if mode == "decl":
            gen.generate_serializer_declaration(p)
        else:
            gen.generate_serializer_definition(p)

    def _emit_struct_serializer(self, p: Printer, struct: Struct, snapshot: int | None, qualified: str, mode: str) -> None:
        gen = ClassGenerator(struct, self._ctx, snapshot=snapshot, qualified=qualified)
        if mode == "decl":
            gen.generate_serializer_declaration(p)
        else:
            gen.generate_serializer_definition(p)

    def _emit_variant_alias_serializer(self, p: Printer, name: str, target: VariantType, mode: str) -> None:
        if mode == "decl":
            p.print("template <>\n")
            p.print(f"struct Serializer<{name}> {{\n")
            p.indent()
            p.print(f"static void serialize(BinaryWriter &stream, const {name} &value);\n")
            p.print(f"static auto deserialize(BinaryReader &stream) -> std::expected<{name}, std::error_code>;\n")
            p.outdent()
            p.print("};\n")
            return
        gen = make_field_generator(target, GenContext(self._ctx, None))
        p.print(f"void Serializer<{name}>::serialize(BinaryWriter &stream, const {name} &value)\n")
        with p.block():
            gen.generate_serialize(p, "value")
        p.print("\n")
        p.print(f"auto Serializer<{name}>::deserialize(BinaryReader &stream) -> std::expected<{name}, std::error_code>\n")
        with p.block():
            p.print(f"{name} out;\n")
            with p.block():
                gen.generate_deserialize(p, "out")
            p.print("return out;\n")

    # --- helpers ------------------------------------------------------------

    def _by_name(self) -> dict[str, Enum | Struct]:
        out: dict[str, Enum | Struct] = {}
        for e in self._file.enums:
            out[e.name] = e
        for s in self._file.structs:
            out[s.name] = s
        return out

    def _unversioned_names(self) -> list[str]:
        return [n for n in self._resolved.declaration_order if not self._resolved.is_versioned(n)]

    def _versioned_names(self) -> list[str]:
        return [n for n in self._resolved.declaration_order if self._resolved.is_versioned(n)]

    def _has_namespaces(self) -> bool:
        return any(self._snapshot_has_entries(s) for s in self._resolved.snapshots)

    def _snapshot_has_entries(self, snap: int) -> bool:
        for name in self._resolved.declaration_order:
            if self._resolved.is_versioned(name) and self._resolved.present_at(name, snap) is not None:
                return True
        return False

    def _has_serializers(self) -> bool:
        for name in self._resolved.declaration_order:
            t = self._by_name()[name]
            if isinstance(t, Enum):
                if t.name in self._ctx.string_coded_enums:
                    return True
            elif t.fields:
                return True
        return any(isinstance(a.target, VariantType) for a in self._file.type_aliases)

    def _version_enum(self) -> Enum | None:
        for f in self._file_set.files.values():
            for e in f.enums:
                if e.name == "ProtocolVersion":
                    return e
        return None


# --- module-free helpers ------------------------------------------------------


def _string_coded_enums(resolved: ResolvedFile) -> frozenset[str]:
    """Module-scope enums encoded by name — they need a `Serializer`
    specialization at namespace scope."""
    out: set[str] = set()

    def walk(t: FieldType | None) -> None:
        if isinstance(t, EnumType):
            if t.scalar is None:
                out.add(t.name)
        elif isinstance(t, (OptionalType, RepeatedType)):
            walk(t.inner)
        elif isinstance(t, VariantType):
            for c in t.cases:
                walk(c)

    for struct in resolved.file.structs:
        for f in struct.fields:
            for version in f.versions:
                walk(version.type)
    for a in resolved.file.type_aliases:
        walk(a.target)
    return frozenset(out)
