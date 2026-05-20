"""`FileGenerator` — orchestrates one C++ header end to end.

protoc analog: `compiler/cpp/cpp_file.{h,cc}`. Assembles a single file
top-to-bottom by routing each section through `Printer`, delegating
to the per-construct generators (`EnumGenerator`, `StructGenerator`,
`SerializerGenerator`) for the type definitions and serializer bodies.
"""

from __future__ import annotations

from ...descriptor import (
    BitsetType,
    CondType,
    Enum,
    EnumType,
    FieldType,
    MappingType,
    OptionalType,
    RepeatedType,
    ResolvedFile,
    Struct,
    VariantType,
)
from .enum import EnumGenerator
from .field import FileContext, cpp_type
from .names import requires_clause, snapshot_namespace
from .printer import Printer
from .serializer import SerializerGenerator
from .struct import StructGenerator


class FileGenerator:
    """One `ResolvedFile` → its C++ header text."""

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
        builtins = resolved.file_set.builtins | frozenset({"UUID"})
        self._ctx = FileContext(
            resolved=resolved,
            known=known,
            builtins=builtins,
            string_coded_enums=_string_coded_enums(resolved),
        )

    # --- public driver ------------------------------------------------------

    def render(self, latest_version: int) -> str:
        p = Printer()
        self._emit_pragma(p)
        self._emit_includes(p)
        self._emit_dep_includes(p)
        p()
        self._emit_namespace_open(p)
        self._emit_primitive_aliases(p)
        self._emit_unversioned(p)
        self._emit_type_aliases(p)
        self._emit_versioned_namespaces(p)
        self._emit_traits(p)
        self._emit_serializers(p)
        self._emit_latest_aliases(p, latest_version)
        self._emit_namespace_close(p)
        return p.text

    # --- includes -----------------------------------------------------------

    def _emit_pragma(self, p: Printer) -> None:
        p("#pragma once")
        p()

    def _emit_includes(self, p: Printer) -> None:
        uses_bitset = self._uses_bitset()
        stdlib = ["<array>", "<cstdint>", "<map>", "<optional>",
                  "<string>", "<variant>", "<vector>"]
        if uses_bitset:
            stdlib.insert(1, "<bitset>")
        for inc in stdlib:
            p(f"#include {inc}")
        if self._has_serializers():
            p()
            p("#include <system_error>")
            p()
            p("#include <bedrock/expected.hpp>")
            p("#include <bedrock/serializer.hpp>")
            p("#include <bedrock/stream.hpp>")
            if uses_bitset:
                p("#include <bedrock/bitset.hpp>")
            if self._uses_uuid():
                p("#include <bedrock/uuid.hpp>")
            if self._uses_nbt():
                p("#include <bedrock/nbt.hpp>")

    def _emit_dep_includes(self, p: Printer) -> None:
        deps = [
            d.replace(".", "/") + ".hpp"
            for d in self._file.imports
            if self._import_has_content(d)
        ]
        if not deps:
            return
        p()
        for d in deps:
            p(f'#include "{d}"')

    # --- namespace ----------------------------------------------------------

    def _emit_namespace_open(self, p: Printer) -> None:
        if self._file.package:
            p(f"namespace {self._file.package.replace('.', '::')} {{")
            p()

    def _emit_namespace_close(self, p: Printer) -> None:
        if self._file.package:
            p()
            p(f"}}  // namespace {self._file.package.replace('.', '::')}")

    # --- type declarations --------------------------------------------------

    def _emit_primitive_aliases(self, p: Printer) -> None:
        from .names import PRIMITIVE_TYPES
        for a in self._file.primitive_aliases:
            p(f"enum {a.name} : {PRIMITIVE_TYPES[a.primitive]} {{}};")
        if (
            self._file.primitive_aliases
            and (self._unversioned_names() or self._file.type_aliases or self._has_namespaces())
        ):
            p()

    def _emit_unversioned(self, p: Printer) -> None:
        names = self._unversioned_names()
        by_name = self._by_name()
        for i, name in enumerate(names):
            if i:
                p()
            self._emit_definition(p, by_name[name])

    def _emit_type_aliases(self, p: Printer) -> None:
        if not self._file.type_aliases:
            return
        if self._unversioned_names():
            p()
        for a in self._file.type_aliases:
            for ref in a.target.referenced:
                if self._resolved.is_versioned(ref):
                    from ...descriptor import CompilerError
                    raise CompilerError(
                        f"{a.name}: a `type` alias cannot reference the "
                        f"versioned type {ref!r}"
                    )
            ctype = cpp_type(a.target, self._ctx, frozenset())
            assert ctype is not None
            p(f"using {a.name} = {ctype};")

    def _emit_versioned_namespaces(self, p: Printer) -> None:
        if not self._has_namespaces():
            return
        if self._unversioned_names() or self._file.type_aliases:
            p()
        emitted_first = False
        for snap in self._resolved.snapshots:
            if not self._snapshot_has_entries(snap):
                continue
            if emitted_first:
                p()
            emitted_first = True
            self._emit_snapshot_namespace(p, snap)

    def _emit_snapshot_namespace(self, p: Printer, snap: int) -> None:
        p(f"namespace {snapshot_namespace(snap)} {{")
        for name in self._resolved.declaration_order:
            if not self._resolved.is_versioned(name):
                continue
            view = self._resolved.present_at(name, snap)
            if view is None:
                continue
            p()
            if view.is_fresh:
                narrowed = view.enum or view.struct
                assert narrowed is not None
                anchor: int | None = None
                if (
                    isinstance(narrowed, Struct)
                    and _has_nested(narrowed)
                    and not _has_versioned_nested(narrowed)
                ):
                    fresh = self._resolved.fresh_snapshots(name)
                    if fresh and fresh[0].lo != snap:
                        anchor = fresh[0].lo
                self._emit_definition(p, narrowed, nested_anchor=anchor)
            else:
                p(f"using {name} = {snapshot_namespace(view.concrete)}::{name};")
        p()
        p(f"}}  // namespace {snapshot_namespace(snap)}")

    def _emit_definition(
        self,
        p: Printer,
        t: Enum | Struct,
        nested_anchor: int | None = None,
    ) -> None:
        if isinstance(t, Enum):
            EnumGenerator(t).emit(p)
        else:
            StructGenerator(
                t, self._ctx, nested_anchor=nested_anchor,
            ).emit(p)

    # --- versioning traits --------------------------------------------------

    def _emit_traits(self, p: Printer) -> None:
        if not self._has_namespaces():
            return
        p()
        p("namespace detail {")
        for i, name in enumerate(self._versioned_names()):
            fresh = self._resolved.fresh_snapshots(name)
            if i:
                p()
            p("template <int V>")
            p(f"struct {name}_;")
            for j, s in enumerate(fresh):
                hi = fresh[j + 1].lo if j + 1 < len(fresh) else None
                clause = requires_clause(s.lo, hi)
                ns = snapshot_namespace(s.lo)
                p()
                p(f"template <int V> requires ({clause})")
                p(f"struct {name}_<V> {{ using type = {ns}::{name}; }};")
        p()
        p("}  // namespace detail")
        p()
        for name in self._versioned_names():
            p(f"template <int V> using {name}_ = typename detail::{name}_<V>::type;")

    # --- serializers --------------------------------------------------------

    def _emit_serializers(self, p: Printer) -> None:
        gen = SerializerGenerator(self._ctx)
        by_name = self._by_name()
        for name in self._resolved.declaration_order:
            t = by_name[name]
            fresh = (
                self._resolved.fresh_snapshots(name)
                if self._resolved.is_versioned(name)
                else ()
            )
            if isinstance(t, Enum):
                if name not in self._ctx.string_coded_enums:
                    continue
                if not fresh:
                    p()
                    gen.emit_for_enum(p, t, None)
                else:
                    for s in fresh:
                        assert s.enum is not None
                        p()
                        gen.emit_for_enum(p, s.enum, s.lo)
            else:
                if not fresh:
                    pos = len(p.lines)
                    p()
                    if not gen.emit_for_struct(p, t, None):
                        del p.lines[pos:]
                else:
                    for s in fresh:
                        assert s.struct is not None
                        pos = len(p.lines)
                        p()
                        if not gen.emit_for_struct(p, t, s.struct, snapshot=s.lo):
                            del p.lines[pos:]
        for a in self._file.type_aliases:
            if isinstance(a.target, VariantType):
                p()
                gen.emit_for_variant_alias(p, a)

    # --- latest aliases -----------------------------------------------------

    def _emit_latest_aliases(self, p: Printer, latest_version: int) -> None:
        if not self._has_namespaces():
            return
        names = self._versioned_names()
        if not names:
            return
        p()
        for name in names:
            p(f"using {name} = {name}_<{latest_version}>;")

    # --- helpers ------------------------------------------------------------

    def _by_name(self) -> dict[str, Enum | Struct]:
        f = self._file
        out: dict[str, Enum | Struct] = {}
        for e in f.enums:
            out[e.name] = e
        for s in f.structs:
            out[s.name] = s
        return out

    def _unversioned_names(self) -> list[str]:
        return [
            n for n in self._resolved.declaration_order
            if not self._resolved.is_versioned(n)
        ]

    def _versioned_names(self) -> list[str]:
        return [
            n for n in self._resolved.declaration_order
            if self._resolved.is_versioned(n)
        ]

    def _has_namespaces(self) -> bool:
        return any(
            self._snapshot_has_entries(s) for s in self._resolved.snapshots
        )

    def _snapshot_has_entries(self, snap: int) -> bool:
        for name in self._resolved.declaration_order:
            if not self._resolved.is_versioned(name):
                continue
            if self._resolved.present_at(name, snap) is not None:
                return True
        return False

    def _import_has_content(self, dep: str) -> bool:
        other = self._file_set.files.get(dep)
        if other is None:
            return False
        return bool(
            other.enums
            or other.structs
            or other.primitive_aliases
            or other.type_aliases
        )

    def _referenced(self) -> frozenset[str]:
        return frozenset().union(
            *(s.referenced for s in self._file.structs),
            *(a.target.referenced for a in self._file.type_aliases),
        )

    def _uses_uuid(self) -> bool:
        return "UUID" in self._referenced()

    def _uses_nbt(self) -> bool:
        return bool(self._referenced() & self._file_set.builtins)

    def _uses_bitset(self) -> bool:
        for s in self._file.structs:
            for f in s.fields:
                for version in f.versions:
                    if _walk_has_bitset(version.type):
                        return True
        for a in self._file.type_aliases:
            if _walk_has_bitset(a.target):
                return True
        return False

    def _has_serializers(self) -> bool:
        for name in self._resolved.declaration_order:
            t = self._by_name()[name]
            if isinstance(t, Enum):
                if t.name in self._ctx.string_coded_enums:
                    return True
            else:
                # Any struct with at least one resolvable field gets a serializer.
                # The cheap check: any field at all.
                if t.fields:
                    return True
        for a in self._file.type_aliases:
            if isinstance(a.target, VariantType):
                return True
        return False


# --- module-free helpers --------------------------------------------------------


def _has_nested(s: Struct) -> bool:
    """A struct has at least one nested type that the dedup logic can anchor.
    Today only nested enums exist; nested structs / aliases plug in here when
    they land."""
    return bool(s.nested_enums)


def _has_versioned_nested(s: Struct) -> bool:
    """At least one nested-enum member carries a `since=` / `until=` /
    `deprecated=` gate, so the enum's snapshot view differs between
    snapshots (either in membership or in which members are marked
    deprecated). The aliasing dedup would point later snapshots at the
    wrong shape, so each fresh snapshot has to emit its own nested-enum
    body."""
    for e in s.nested_enums:
        for v in e.values:
            if (
                v.since is not None
                or v.until is not None
                or v.deprecated is not None
            ):
                return True
    return False


def _walk_has_bitset(t: FieldType | None) -> bool:
    if t is None:
        return False
    if isinstance(t, BitsetType):
        return True
    if isinstance(t, (OptionalType, CondType, RepeatedType)):
        return _walk_has_bitset(t.inner)
    if isinstance(t, MappingType):
        return _walk_has_bitset(t.key) or _walk_has_bitset(t.value)
    if isinstance(t, VariantType):
        return any(_walk_has_bitset(c) for c in t.cases)
    return False


def _string_coded_enums(resolved: ResolvedFile) -> frozenset[str]:
    """Module-scope enums some field encodes by name — they need a
    `Serializer` specialization. Integer-coded ones inline a cast."""
    out: set[str] = set()
    for struct in resolved.file.structs:
        for f in struct.fields:
            for version in f.versions:
                t = version.type
                while isinstance(t, (OptionalType, CondType)):
                    t = t.inner
                if isinstance(t, EnumType) and t.scalar is None:
                    out.add(t.name)
    return frozenset(out)
