"""`FileGenerator` — assembles one C++ header/source pair end to end.

protoc analog: `compiler/cpp/cpp_file.{h,cc}`. Routes each section through a
`Printer`, delegating type definitions and serializers to `EnumGenerator` /
`MessageGenerator` and the `FieldGenerator` codec.

The `.hpp` holds type definitions, the raw-`int` `_<V>` version selector, and
declaration-only `Serializer<T>` specializations; the `.cpp` holds the
out-of-line serializer bodies, compiled once into the static lib.
"""

from __future__ import annotations

from collections.abc import Iterator

from bedrock_protocol.descriptor import (
    LEGACY_SCOPE,
    Enum,
    EnumType,
    FieldType,
    MappingType,
    OptionalType,
    PrimitiveType,
    RepeatedType,
    ResolvedFile,
    Struct,
    TypeAlias,
    VariantType,
    split_scope,
)

from .enum import EnumGenerator
from .field import FileContext, GenContext, cpp_type, make_field_generator, type_includes
from .helpers import (
    BUILTIN_HEADERS,
    PRIMITIVE_TYPES,
    bare_name,
    cpp_qualified,
    outermost,
    requires_clause,
    snapshot_namespace,
)
from .message import MessageGenerator
from .printer import Printer

#: One nested type as the backend needs it: its descriptor, its dotted IR name,
#: its C++ spelling, and the snapshot its serializer body should be built at.
NestedView = tuple[Enum | Struct, str, str, int | None]


class FileGenerator:
    def __init__(self, resolved: ResolvedFile) -> None:
        self._resolved = resolved
        self._file = resolved.file
        self._file_set = resolved.pool.file_set
        known = frozenset(BUILTIN_HEADERS) | frozenset(
            name
            for f in resolved.pool.file_set.files.values()
            for name in (
                *(e.key for e in f.enums),
                *(s.key for s in f.structs),
                *(n for s in f.structs for n in _nested_names(s, s.key)),
                *(a.name for a in f.primitive_aliases),
                *(a.name for a in f.type_aliases),
            )
        )
        self._ctx = FileContext(
            resolved=resolved,
            known=known,
            string_coded_enums=_string_coded_enums(resolved),
        )
        self._header_includes: set[str] = set()
        self._versioned_alias_cache: tuple[TypeAlias, ...] | None = None

    # --- public driver ------------------------------------------------------

    def render_header(self, latest_version: int) -> str:
        # Render the body first; the generators record their includes on the
        # Printer as they print. Then stamp the collected set at the top.
        body = Printer()
        self._emit_namespace_open(body)
        self._emit_primitive_aliases(body)
        self._emit_unversioned(body)
        self._emit_type_aliases(body)
        self._emit_versioned_namespaces(body)
        self._emit_traits(body)
        self._emit_legacy_traits(body, latest_version)
        self._emit_packet_traits(body)
        self._emit_enum_reflections(body)
        self._emit_serializers(body, mode="decl")
        self._emit_latest_aliases(body, latest_version)
        self._emit_namespace_close(body)
        self._header_includes = set(body.includes) | self._builtin_includes()

        p = Printer()
        p.print("#pragma once\n\n")
        self._emit_includes(p, self._header_includes)
        self._emit_generated_includes(p)
        p.print("\n")
        p.print(body.text)
        return p.text

    def render_source(self) -> str:
        body = Printer()
        self._emit_namespace_open(body)
        self._emit_serializers(body, mode="def")
        self._emit_namespace_close(body)

        p = Printer()
        p.print(f'#include "{self._file.stem}.h"\n')
        # Only what the bodies need beyond what the header already pulls in.
        extra = body.includes - self._header_includes
        if extra:
            p.print("\n")
            self._emit_includes(p, extra)
        p.print("\n")
        p.print(body.text)
        return p.text

    # --- includes -----------------------------------------------------------

    def _emit_includes(self, p: Printer, includes: set[str]) -> None:
        """Emit `includes` in two sorted groups: stdlib then bedrock headers."""
        std = sorted(i for i in includes if not i.startswith("<bedrock/"))
        project = sorted(i for i in includes if i.startswith("<bedrock/"))
        for inc in std:
            p.print(f"#include {inc}\n")
        if project:
            if std:
                p.print("\n")
            for inc in project:
                p.print(f"#include {inc}\n")

    def _emit_generated_includes(self, p: Printer) -> None:
        """Headers this file's own header needs: the owner of every type it
        references but another file declares. The umbrella header includes every
        generated header, but in sorted order, so a header that leans on it compiles
        only by luck of the alphabet -- and never standalone."""
        needed: set[str] = set()
        owners = self._type_owners()
        for ref in self._referenced_names():
            owner = owners.get(ref)
            if owner is not None:
                needed.add(owner)
        if not needed:
            return
        p.print("\n")
        for name in sorted(needed):
            p.print(f'#include "{name.replace(".", "/")}.h"\n')

    def _type_owners(self) -> dict[str, str]:
        """Type name -> the module declaring it, for every file but this one. Only
        files that name a package emit a header; the DSL surface itself does not.
        Builtins are excluded -- they live in a hand-written header, not a
        generated one (see `_builtin_includes`)."""
        owners: dict[str, str] = {}
        for name, f in self._file_set.files.items():
            if f is self._file or not f.package:
                continue
            for declared in (
                *(e.key for e in f.enums),
                *(s.key for s in f.structs if not s.builtin),
                *(a.name for a in f.primitive_aliases),
                *(a.name for a in f.type_aliases),
            ):
                owners[declared] = name
        return owners

    def _builtin_includes(self) -> set[str]:
        """`<bedrock/<stem>.hpp>` for every builtin this file references: the
        compiler emits no definition for those, so the hand-written header that
        does define them has to come in."""
        homes: dict[str, str] = {}
        for name, f in self._file_set.files.items():
            # Take the header from the module's own name: `stem` is only set for
            # files named on the command line, and falls back to the dotted path.
            for struct in f.structs:
                if struct.builtin:
                    homes[struct.key] = name.rsplit(".", 1)[-1]
        out = {f"<bedrock/{homes[r]}.hpp>" for r in self._referenced_names() if r in homes}
        return out | {BUILTIN_HEADERS[r] for r in self._referenced_names() if r in BUILTIN_HEADERS}

    def _referenced_names(self) -> set[str]:
        out: set[str] = set()
        for struct in self._file.structs:
            out |= {r.split(".", 1)[0] for r in struct.referenced}
        for alias in self._file.type_aliases:
            out |= {r.split(".", 1)[0] for r in alias.target.referenced}
        return out

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
            p.add_includes(*type_includes(PrimitiveType(name=a.primitive)))
            p.print(f"enum {a.name} : {PRIMITIVE_TYPES[a.primitive]} {{}};\n")
        if self._file.primitive_aliases:
            p.print("\n")

    def _emit_unversioned(self, p: Printer) -> None:
        by_name = self._by_name()
        with _FlavourScope(p) as scope:
            for name in self._unversioned_names():
                t = by_name[name]
                if isinstance(t, Struct) and t.builtin:
                    continue  # hand-written in <bedrock/*.hpp>
                scope.enter(name)
                self._emit_definition(p, t)
                p.print("\n")

    def _emit_type_aliases(self, p: Printer) -> None:
        plain = [a for a in self._file.type_aliases if a not in self._versioned_aliases()]
        for a in plain:
            ctype = cpp_type(a.target, self._ctx)
            assert ctype is not None
            p.add_includes(*type_includes(a.target))
            p.print(f"using {a.name} = {ctype};\n")
        if plain:
            p.print("\n")

    def _emit_versioned_namespaces(self, p: Printer) -> None:
        """One namespace per snapshot, holding that snapshot's view of every
        versioned type in topological order.

        Pre-cereal declarations sit in `legacy::vN` rather than `vN::legacy`, so
        a `legacy::` qualifier written from inside a snapshot namespace cannot
        find the enclosing namespace itself. Order is what makes the two trees
        work together: references cross both ways -- a cerealised LevelSettings
        reaches the pre-cereal GameRule while a pre-cereal type may reach a
        cerealised one -- so the walk follows the topological order and reopens
        whichever namespace the next type belongs to."""
        for snap in self._resolved.snapshots:
            ns = snapshot_namespace(snap)
            with _FlavourScope(p, ns) as scope:
                for name in self._versioned_names():
                    view = self._resolved.present_at(name, snap)
                    if view is None:
                        continue
                    scope.enter(name)
                    if view.is_fresh:
                        self._emit_definition(p, view.enum or view.struct, self._nested_anchor(name, snap), snap)
                    else:
                        bare = bare_name(name)
                        p.print(f"using {bare} = {snapshot_namespace(view.concrete)}::{bare};\n")
                    p.print("\n")
                # An alias over versioned types lands in the namespace too: its
                # spelling changes with the snapshot its cases resolve to. An
                # alias names no flavour, so it is always cerealised.
                for a in self._versioned_aliases():
                    alias_view = self._alias_view(a, snap)
                    if alias_view is None:
                        continue
                    spelling, concrete = alias_view
                    scope.enter(a.name)
                    p.add_includes(*type_includes(a.target))
                    target = spelling if concrete == snap else f"{snapshot_namespace(concrete)}::{a.name}"
                    p.print(f"using {a.name} = {target};\n\n")

    def _emit_legacy_traits(self, p: Printer, latest_version: int) -> None:
        """The `_<V>` selectors over the pre-cereal declarations. They follow
        every definition, and `packet_of` follows them."""
        if not self._versioned_entries(cereal=False):
            return
        p.print(f"namespace {LEGACY_SCOPE} {{\n\n")
        self._emit_traits(p, cereal=False)
        self._emit_latest_aliases(p, latest_version, cereal=False)
        p.print(f"}}  // namespace {LEGACY_SCOPE}\n\n")

    def _emit_definition(
        self,
        p: Printer,
        t: Enum | Struct | None,
        nested_anchor: int | None = None,
        snapshot: int | None = None,
    ) -> None:
        if isinstance(t, Enum):
            EnumGenerator(t).generate_definition(p)
        elif isinstance(t, Struct):
            MessageGenerator(
                t, self._ctx, snapshot=snapshot, nested_anchor=nested_anchor
            ).generate_class_definition(p)

    # --- nested types -------------------------------------------------------

    def _nested_anchor(self, name: str, snapshot: int) -> int | None:
        """The snapshot whose namespace owns `name`'s nested definitions, or
        None when this snapshot must define them itself. A nested type that
        neither version-gates itself nor reaches a versioned type has one shape
        across the owner's snapshots, so the first one defines it and the rest
        alias it -- and it stays a single C++ type."""
        fresh = self._resolved.fresh_snapshots(name)
        if not fresh or fresh[0].lo == snapshot:
            return None
        t = self._by_name().get(name)
        if not isinstance(t, Struct) or self._nested_is_versioned(t, name):
            return None
        return fresh[0].lo

    def _nested_is_versioned(self, struct: Struct, owner: str) -> bool:
        """Whether any of `struct`'s nested types changes shape across
        snapshots -- by its own `since=` / `until=`, or by reaching a versioned
        type. References back into `owner` are its own snapshots, not a change."""
        for inner in struct.nested:
            if inner.change_points:
                return True
            if isinstance(inner, Struct):
                refs = {outermost(r) for r in inner.referenced} - {owner}
                if any(self._resolved.is_versioned(r) for r in refs):
                    return True
                if self._nested_is_versioned(inner, owner):
                    return True
        return False

    def _nested_views(self, name: str) -> list[NestedView]:
        """Every type nested in `name`, innermost first, once per distinct C++
        type: one pass for an unversioned or anchored owner, one per fresh
        snapshot when the nested shapes disagree across them."""
        t = self._by_name().get(name)
        if not isinstance(t, Struct) or not t.nested:
            return []
        out: list[NestedView] = []
        if not self._resolved.is_versioned(name):
            _collect_nested(t, name, cpp_qualified(name), None, out)
            return out
        fresh = self._resolved.fresh_snapshots(name)
        heads = fresh if self._nested_is_versioned(t, name) else fresh[:1]
        for s in heads:
            assert s.struct is not None
            _collect_nested(s.struct, name, cpp_qualified(name, s.lo), s.lo, out)
        return out

    # --- versioning traits + selector --------------------------------------

    def _emit_traits(self, p: Printer, cereal: bool = True) -> None:
        entries = self._versioned_entries(cereal)
        if not entries:
            return
        p.print("namespace detail {\n")
        for name, los, until in entries:
            bare = bare_name(name)
            p.print("\n")
            p.print("template <int V>\n")
            p.print(f"struct {bare}_;\n")
            for j, lo in enumerate(los):
                hi = los[j + 1] if j + 1 < len(los) else until
                p.print("\n")
                p.print(f"template <int V> requires ({requires_clause(lo, hi)})\n")
                p.print(f"struct {bare}_<V> {{ using type = {snapshot_namespace(lo)}::{bare}; }};\n")
        p.print("\n}  // namespace detail\n\n")
        for name, _, _ in entries:
            bare = bare_name(name)
            p.print(f"template <int V> using {bare}_ = typename detail::{bare}_<V>::type;\n")
        p.print("\n")

    def _emit_packet_traits(self, p: Printer) -> None:
        """`packet_of<V, Id>` for every packet declared here, so a caller can
        reach a packet by wire id without naming the type. The primary in
        <bedrock/packet.hpp> answers `void`, so the constraint has to be the
        packet's whole `[since, until)` range -- outside it the packet is not on
        the wire and must not resolve."""
        entries = self._packet_entries()
        if not entries:
            return
        p.add_includes("<bedrock/packet.hpp>")
        for packet_id, spelling, clause in entries:
            p.print(f"template <int V>{f' requires ({clause})' if clause else ''}\n")
            p.print(f"struct packet_of<V, {packet_id}> {{ using type = {spelling}; }};\n\n")

    def _packet_entries(self) -> list[tuple[int, str, str]]:
        """`(id, type spelling, requires clause)` per packet, by id. A versioned
        packet hands back its `_<V>` selector rather than one specialization per
        snapshot -- the selector already dispatches within the range."""
        by_name = self._by_name()
        out: list[tuple[int, str, str]] = []
        for name in self._resolved.declaration_order:
            t = by_name.get(name)
            if not isinstance(t, Struct) or t.packet_id is None:
                continue
            if self._resolved.is_versioned(name):
                fresh = self._resolved.fresh_snapshots(name)
                scope, _ = split_scope(name)
                selector = f"{bare_name(name)}_<V>"
                spelling = f"{scope}::{selector}" if scope is not None else selector
                out.append((t.packet_id, spelling, requires_clause(fresh[0].lo, t.until)))
            else:
                out.append((t.packet_id, cpp_qualified(name), ""))
        return sorted(out)

    def _emit_latest_aliases(self, p: Printer, latest_version: int, cereal: bool = True) -> None:
        for name, _, until in self._versioned_entries(cereal):
            if until is not None and latest_version >= until:
                continue
            bare = bare_name(name)
            p.print(f"using {bare} = {bare}_<{latest_version}>;\n")

    # --- reflection ---------------------------------------------------------

    def _emit_enum_reflections(self, p: Printer) -> None:
        by_name = self._by_name()
        views: list[tuple[Enum, str, str]] = []
        for name in self._resolved.declaration_order:
            t = by_name[name]
            if isinstance(t, Struct):
                views += [
                    (inner, qualified, bare_name(dotted))
                    for inner, dotted, qualified, _ in self._nested_views(name)
                    if isinstance(inner, Enum)
                ]
                continue
            if self._resolved.is_versioned(name):
                for s in self._resolved.fresh_snapshots(name):
                    assert s.enum is not None
                    views.append((s.enum, cpp_qualified(name, s.lo), bare_name(name)))
            else:
                views.append((t, cpp_qualified(name), bare_name(name)))
        # the empty primary already covers a memberless enum
        views = [v for v in views if v[0].values]
        if not views:
            return
        p.print("namespace detail {\n")
        for enum, qualified, type_name in views:
            p.print("\n")
            EnumGenerator(enum).generate_reflection(p, qualified, type_name)
        p.print("\n}  // namespace detail\n\n")

    # --- serializers --------------------------------------------------------

    def _emit_serializers(self, p: Printer, mode: str) -> None:
        by_name = self._by_name()
        for name in self._resolved.declaration_order:
            t = by_name[name]
            if isinstance(t, Struct) and t.builtin:
                continue  # Serializer<T> is hand-written alongside the type
            if isinstance(t, Enum):
                # One specialization per distinct C++ type, as for a struct: a
                # versioned enum is a type per fresh snapshot, and its users
                # spell it snapshot-qualified.
                if name not in self._ctx.string_coded_enums:
                    continue
                if self._resolved.is_versioned(name):
                    for s in self._resolved.fresh_snapshots(name):
                        assert s.enum is not None
                        p.print("\n")
                        self._emit_enum_serializer(p, s.enum, cpp_qualified(name, s.lo), mode)
                else:
                    p.print("\n")
                    self._emit_enum_serializer(p, t, cpp_qualified(name), mode)
                continue
            # Nested types first, so the owner's body sees them already declared.
            for inner, dotted, qualified, snapshot in self._nested_views(name):
                if isinstance(inner, Enum):
                    if dotted in self._ctx.string_coded_enums:
                        p.print("\n")
                        self._emit_enum_serializer(p, inner, qualified, mode)
                elif _has_wire_shape(inner):
                    p.print("\n")
                    self._emit_struct_serializer(p, inner, snapshot, qualified, mode)
            if not _has_wire_shape(t):
                continue
            if self._resolved.is_versioned(name):
                for s in self._resolved.fresh_snapshots(name):
                    assert s.struct is not None
                    p.print("\n")
                    self._emit_struct_serializer(p, s.struct, s.lo, cpp_qualified(name, s.lo), mode)
            else:
                p.print("\n")
                self._emit_struct_serializer(p, t, None, cpp_qualified(name), mode)
        for a in self._file.type_aliases:
            if not isinstance(a.target, VariantType):
                continue
            if a in self._versioned_aliases():
                for lo, _, concrete in self._alias_plan(a):
                    if concrete != lo:
                        continue
                    p.print("\n")
                    self._emit_variant_alias_serializer(p, f"{snapshot_namespace(lo)}::{a.name}", a.target, mode, lo)
            else:
                p.print("\n")
                self._emit_variant_alias_serializer(p, a.name, a.target, mode, None)

    def _emit_enum_serializer(self, p: Printer, enum: Enum, qualified: str, mode: str) -> None:
        gen = EnumGenerator(enum, qualified)
        if mode == "decl":
            gen.generate_serializer_declaration(p)
        else:
            gen.generate_serializer_definition(p)

    def _emit_struct_serializer(
        self, p: Printer, struct: Struct, snapshot: int | None, qualified: str, mode: str
    ) -> None:
        gen = MessageGenerator(struct, self._ctx, snapshot=snapshot, qualified=qualified)
        if mode == "decl":
            gen.generate_serializer_declaration(p)
        else:
            gen.generate_serializer_definition(p)

    def _emit_variant_alias_serializer(
        self, p: Printer, name: str, target: VariantType, mode: str, snapshot: int | None
    ) -> None:
        if mode == "decl":
            p.add_includes("<bedrock/serializer.hpp>", "<bedrock/stream.hpp>", "<expected>", "<system_error>")
            p.print("template <>\n")
            p.print(f"struct Serializer<{name}> {{\n")
            p.indent()
            p.print(f"static void serialize(BinaryWriter &stream, const {name} &value);\n")
            p.print(f"static auto deserialize(BinaryReader &stream) -> std::expected<{name}, std::error_code>;\n")
            p.outdent()
            p.print("};\n")
            return
        p.add_includes("<bedrock/serializer.hpp>", "<bedrock/stream.hpp>")
        gen = make_field_generator(target, GenContext(self._ctx, snapshot))
        p.print(f"void Serializer<{name}>::serialize(BinaryWriter &stream, const {name} &value)\n")
        with p.block():
            gen.generate_serialize(p, "value")
        p.print("\n")
        p.print(
            f"auto Serializer<{name}>::deserialize(BinaryReader &stream) -> std::expected<{name}, std::error_code>\n"
        )
        with p.block():
            p.print(f"{name} out;\n")
            with p.block():
                gen.generate_deserialize(p, "out")
            p.print("return out;\n")

    # --- helpers ------------------------------------------------------------

    def _by_name(self) -> dict[str, Enum | Struct]:
        out: dict[str, Enum | Struct] = {}
        for e in self._file.enums:
            out[e.key] = e
        for s in self._file.structs:
            out[s.key] = s
        return out

    def _unversioned_names(self) -> list[str]:
        return [n for n in self._resolved.declaration_order if not self._resolved.is_versioned(n)]

    def _versioned_names(self, cereal: bool | None = None) -> list[str]:
        return [
            n
            for n in self._resolved.declaration_order
            if self._resolved.is_versioned(n) and (cereal is None or _is_legacy(n) != cereal)
        ]

    def _versioned_aliases(self) -> tuple[TypeAlias, ...]:
        """Aliases whose target reaches a versioned type, so the alias is itself
        one shape per snapshot."""
        if self._versioned_alias_cache is None:
            self._versioned_alias_cache = tuple(
                a
                for a in self._file.type_aliases
                if any(self._resolved.is_versioned(r.split(".", 1)[0]) for r in a.target.referenced)
            )
        return self._versioned_alias_cache

    def _alias_plan(self, alias: TypeAlias) -> tuple[tuple[int, str, int], ...]:
        """`(snapshot, spelling, concrete)` per snapshot the alias is spellable
        at. Two snapshots spelling the same C++ type share one definition -- a
        `using` names a type rather than making one, so a second definition
        would redeclare that type's `Serializer`."""
        plan: list[tuple[int, str, int]] = []
        first: dict[str, int] = {}
        roots = {r.split(".", 1)[0] for r in alias.target.referenced}
        for snap in self._resolved.snapshots:
            if any(self._resolved.is_versioned(r) and self._resolved.present_at(r, snap) is None for r in roots):
                continue
            spelling = cpp_type(alias.target, self._ctx, snap)
            if spelling is None:
                continue
            plan.append((snap, spelling, first.setdefault(spelling, snap)))
        return tuple(plan)

    def _alias_view(self, alias: TypeAlias, snapshot: int) -> tuple[str, int] | None:
        for lo, spelling, concrete in self._alias_plan(alias):
            if lo == snapshot:
                return spelling, concrete
        return None

    def _versioned_entries(self, cereal: bool = True) -> list[tuple[str, tuple[int, ...], int | None]]:
        """Every versioned name with the snapshots holding a fresh definition and
        the version it disappears at, for the `_<V>` selector."""
        by_name = self._by_name()
        entries = [
            (
                name,
                tuple(s.lo for s in self._resolved.fresh_snapshots(name)),
                getattr(by_name.get(name), "until", None),
            )
            for name in self._versioned_names(cereal)
        ]
        for a in self._versioned_aliases() if cereal else ():
            los = tuple(lo for lo, _, concrete in self._alias_plan(a) if lo == concrete)
            if los:
                entries.append((a.name, los, None))
        return entries

    def _snapshot_has_entries(self, snap: int) -> bool:
        return any(self._resolved.present_at(n, snap) is not None for n in self._versioned_names())


# --- module-free helpers ------------------------------------------------------


def _is_legacy(name: str) -> bool:
    return split_scope(name)[0] is not None


class _FlavourScope:
    """Opens and closes the namespace a declaration belongs to as a walk moves
    between the cerealised and pre-cereal trees, so one topological pass can emit
    both. Namespaces reopen freely in C++, so a run costs one pair of braces and
    a schema with no pre-cereal declaration gets exactly one."""

    def __init__(self, p: Printer, snapshot_ns: str | None = None) -> None:
        self._p = p
        self._ns = snapshot_ns
        self._open: str | None = None

    def __enter__(self) -> "_FlavourScope":
        return self

    def __exit__(self, *exc: object) -> None:
        self._close()

    def enter(self, name: str) -> None:
        scope = LEGACY_SCOPE if _is_legacy(name) else ""
        if self._open == scope:
            return
        self._close()
        if scope:
            self._p.print(f"namespace {scope} {{\n\n")
        if self._ns is not None:
            self._p.print(f"namespace {self._ns} {{\n\n")
        self._open = scope

    def _close(self) -> None:
        if self._open is None:
            return
        if self._ns is not None:
            self._p.print(f"}}  // namespace {self._ns}\n\n")
        if self._open:
            self._p.print(f"}}  // namespace {self._open}\n\n")
        self._open = None


def _has_wire_shape(struct: Struct) -> bool:
    """A struct declared only to scope its nested types carries nothing on the
    wire, so it gets no `Serializer`. A leaf with no fields and no nesting still
    does -- it can stand as a zero-byte variant alternative."""
    return bool(struct.fields) or not struct.nested


def _nested_names(struct: Struct, prefix: str) -> Iterator[str]:
    """Every dotted name declared inside `struct`, at any depth."""
    for inner in struct.nested:
        qualified = f"{prefix}.{inner.name}"
        yield qualified
        if isinstance(inner, Struct):
            yield from _nested_names(inner, qualified)


def _collect_nested(struct: Struct, dotted: str, qualified: str, snapshot: int | None, out: list[NestedView]) -> None:
    """Append `struct`'s nested types innermost-first, so a serializer emitted
    in this order always follows the ones its body calls into."""
    for inner in struct.nested:
        inner_dotted, inner_qualified = f"{dotted}.{inner.name}", f"{qualified}::{inner.name}"
        if isinstance(inner, Struct):
            _collect_nested(inner, inner_dotted, inner_qualified, snapshot, out)
        out.append((inner, inner_dotted, inner_qualified, snapshot))


def _string_coded_enums(resolved: ResolvedFile) -> frozenset[str]:
    """Enums encoded by name — they need a `Serializer` specialization at
    namespace scope. Keyed by dotted IR name, so a nested one is distinct."""
    out: set[str] = set()

    def walk(t: FieldType | None) -> None:
        if isinstance(t, EnumType):
            if t.scalar is None:
                out.add(t.name)
        elif isinstance(t, (OptionalType, RepeatedType)):
            walk(t.inner)
        elif isinstance(t, MappingType):
            walk(t.key)
            walk(t.value)
        elif isinstance(t, VariantType):
            for c in t.cases:
                walk(c)

    def walk_struct(struct: Struct) -> None:
        for f in struct.fields:
            for version in f.versions:
                walk(version.type)
        for inner in struct.nested:
            if isinstance(inner, Struct):
                walk_struct(inner)

    for struct in resolved.file.structs:
        walk_struct(struct)
    for a in resolved.file.type_aliases:
        walk(a.target)
    return frozenset(out)
