"""Frontend — `.py` DSL files to `File` instances.

Analog of protoc's `io::Tokenizer` + `compiler::Parser`. We use griffe to
statically parse the user's Python source — the DSL decorators
(`@packet`, `@type`, `field()`, `value()`) are no-ops at runtime, so griffe
never executes them, only reads them as AST.

A `SourceTree` follows `from X.Y import ...` references between modules so a
struct in one file can reference a type declared in another. Every file the
sourcetree loads becomes a `File` in the resulting `FileSet`; files passed
to `load_all()` are also listed as `outputs` so the CLI knows which ones to
emit.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field, replace
from pathlib import Path
from typing import Iterator, cast

import griffe

from ..descriptor import (
    INTEGER_PRIMITIVES,
    PRIMITIVES,
    VARINT_PRIMITIVES,
    BitsetType,
    CompilerError,
    CondType,
    Enum,
    EnumType,
    EnumValue,
    Field,
    FieldVersion,
    FieldType,
    File,
    FileSet,
    MappingType,
    OptionalType,
    Predicate,
    PrimitiveAlias,
    PrimitiveType,
    RepeatedType,
    Struct,
    StructType,
    TypeAlias,
    VariantType,
)
from . import extensions

_Ann = griffe.Expr | str | None


@dataclass(frozen=True)
class _TagSpec:
    """Resolved `field(tag=...)` for a tagged-union discriminator: `primitive`
    is the wire form, `enum_name` is the optional `IntEnum` whose members
    supply the C++ case labels (one-to-one with the variant alternatives in
    declaration order)."""
    primitive: PrimitiveType
    enum_name: str | None = None


@dataclass
class _ClassifyResult:
    """Output of the cross-module classification pass — immutable from
    `_lower_file`'s point of view, so no mid-pipeline mutation."""
    enum_names: frozenset[str]
    struct_names: frozenset[str]
    builtins: frozenset[str]
    aliases_by_name: dict[str, PrimitiveAlias | TypeAlias]
    primitive_aliases_by_module: dict[str, tuple[PrimitiveAlias, ...]]
    type_aliases_by_module: dict[str, tuple[TypeAlias, ...]]


class SourceTree:
    """Loads `.py` DSL files via griffe, lowers them to `File`.

    `import_paths` are the directories the loader uses to resolve `from X.Y
    import ...` references between modules — protoc's `--proto_path` equivalent.
    """

    def __init__(self, import_paths: list[Path]) -> None:
        self._import_paths = [p.resolve() for p in import_paths]
        # Shared across every griffe.load: keeps version-redeclared attributes
        # griffe's name-keyed mapping would otherwise collapse.
        self._extensions = griffe.Extensions(extensions.RedeclarationExtension())

    # --- public API ---------------------------------------------------------

    def load_all(self, sources: tuple[Path, ...]) -> FileSet:
        """Load every source file plus its transitive imports, returning the
        complete `FileSet`. The order in `sources` is preserved in `outputs`.
        """
        griffe_modules: dict[str, griffe.Module] = {}
        stems: dict[str, str] = {}
        output_names: list[str] = []
        for src in sources:
            name, root = self._module_name_and_root(src)
            griffe_modules[name] = self._griffe_load(name, root)
            stems[name] = src.stem
            output_names.append(name)
        self._follow_imports(griffe_modules, output_names)
        classified = self._classify(griffe_modules)
        files = {
            name: self._lower_file(name, mod, stems.get(name, name), griffe_modules, classified)
            for name, mod in griffe_modules.items()
        }
        return FileSet(
            files=files,
            outputs=tuple(output_names),
            builtins=classified.builtins,
            version=_dsl_version(griffe_modules),
        )

    # --- griffe loading -----------------------------------------------------

    def _griffe_load(self, name: str, root: Path) -> griffe.Module:
        return cast(griffe.Module, griffe.load(
            name,
            search_paths=[str(root)],
            allow_inspection=False,
            extensions=self._extensions,
        ))

    def _module_name_and_root(self, path: Path) -> tuple[str, Path]:
        path = path.resolve()
        for ip in self._import_paths:
            try:
                rel = path.relative_to(ip)
            except ValueError:
                continue
            return ".".join(rel.with_suffix("").parts), ip
        parent = path.parent
        name = f"{parent.name}.{path.stem}" if parent.name else path.stem
        return name, parent

    def _follow_imports(
        self,
        loaded: dict[str, griffe.Module],
        seed: list[str],
    ) -> None:
        pending = list(seed)
        while pending:
            for dep in self._imports_of(loaded[pending.pop()]):
                if dep in loaded:
                    continue
                parts = dep.split(".")
                for ip in self._import_paths:
                    module = ip.joinpath(*parts).with_suffix(".py")
                    package = ip.joinpath(*parts, "__init__.py")
                    if module.is_file() or package.is_file():
                        loaded[dep] = self._griffe_load(dep, ip)
                        pending.append(dep)
                        break

    @staticmethod
    def _imports_of(mod: griffe.Module) -> set[str]:
        """Source modules `mod`'s `from X.Y import ...` lines refer to.
        Names with a `_`-prefixed component (the DSL itself) are omitted.
        """
        out: set[str] = set()
        for member in mod.members.values():
            target = getattr(member, "target_path", None)
            if target is None or "." not in str(target):
                continue
            dep = str(target).rsplit(".", 1)[0]
            if not any(part.startswith("_") for part in dep.split(".")):
                out.add(dep)
        return out

    # --- classification (across every loaded module) ------------------------

    def _classify(self, loaded: dict[str, griffe.Module]) -> _ClassifyResult:
        enum_names: set[str] = set()
        struct_names: set[str] = set()
        builtins: set[str] = set()
        aliases_by_name: dict[str, PrimitiveAlias | TypeAlias] = {}
        primitive_aliases_by_module: dict[str, tuple[PrimitiveAlias, ...]] = {}
        type_aliases_by_module: dict[str, tuple[TypeAlias, ...]] = {}

        def collect(cls: griffe.Class, prefix: str) -> None:
            """Record a class and recurse into its nested non-enum, non-builtin
            classes, registering each under its dotted path so a field
            annotation like `Parent.Child` resolves to a struct."""
            full = cls.name if not prefix else f"{prefix}.{cls.name}"
            if _is_int_enum(cls):
                enum_names.add(full)
                return
            struct_names.add(full)
            for inner in cls.classes.values():
                if inner.is_alias or _is_builtin_class(inner):
                    continue
                collect(inner, full)

        for mod in loaded.values():
            for cls in mod.classes.values():
                if cls.is_alias:
                    continue
                if _is_builtin_class(cls):
                    builtins.add(cls.name)
                    continue
                collect(cls, "")

        # Alias pass — must run after classification because an alias may
        # reference any class anywhere; within this pass declaration order
        # is the resolution order so an alias may reference an earlier one.
        for name, mod in loaded.items():
            primitives: list[PrimitiveAlias] = []
            others: list[TypeAlias] = []
            sources = list(mod.attributes.items()) + list(mod.type_aliases.items())
            ctx = _AnnotationContext(
                enum_names=frozenset(enum_names),
                struct_names=frozenset(struct_names),
                builtins=frozenset(builtins),
                aliases=aliases_by_name,
            )
            for attr_name, attr in sources:
                if attr_name == "package" or attr_name in PRIMITIVES or attr.value is None:
                    continue
                # `from X import Y` re-exports a name griffe surfaces in the same
                # mapping local PEP-695 aliases live in. Treat it as a reference,
                # not a fresh declaration -- the home module already owns the
                # definition we'd otherwise duplicate.
                if getattr(attr, "is_alias", False):
                    continue
                alias = ctx.parse_alias(attr_name, attr.value)
                if alias is None:
                    continue
                aliases_by_name[alias.name] = alias
                if isinstance(alias, PrimitiveAlias):
                    primitives.append(alias)
                else:
                    others.append(alias)
            primitive_aliases_by_module[name] = tuple(primitives)
            type_aliases_by_module[name] = tuple(others)

        return _ClassifyResult(
            enum_names=frozenset(enum_names),
            struct_names=frozenset(struct_names),
            builtins=frozenset(builtins),
            aliases_by_name=aliases_by_name,
            primitive_aliases_by_module=primitive_aliases_by_module,
            type_aliases_by_module=type_aliases_by_module,
        )

    # --- lowering -----------------------------------------------------------

    def _lower_file(
        self,
        name: str,
        mod: griffe.Module,
        stem: str,
        loaded: dict[str, griffe.Module],
        classified: _ClassifyResult,
    ) -> File:
        ctx = _AnnotationContext(
            enum_names=classified.enum_names,
            struct_names=classified.struct_names,
            builtins=classified.builtins,
            aliases=classified.aliases_by_name,
        )
        enums: list[Enum] = []
        structs: list[Struct] = []
        order: list[str] = []
        for cls in mod.classes.values():
            if cls.is_alias or cls.name in classified.builtins:
                continue
            redecls = cls.extra.get(extensions.EXTRA_NAMESPACE, {}).get(
                extensions.CLASS_REDECLARATIONS
            )
            if redecls is not None:
                struct = ctx.merged_struct(redecls)
                structs.append(struct)
                order.append(struct.name)
            elif _is_int_enum(cls):
                enum = ctx.enum(cls)
                enums.append(enum)
                order.append(enum.name)
            else:
                struct = ctx.struct(cls)
                structs.append(struct)
                order.append(struct.name)
        imports = tuple(
            sorted(
                d for d in self._imports_of(mod)
                if d in loaded and d != name
            )
        )
        return File(
            name=name,
            stem=stem,
            package=_package_of(mod),
            enums=tuple(enums),
            structs=tuple(structs),
            primitive_aliases=classified.primitive_aliases_by_module[name],
            type_aliases=classified.type_aliases_by_module[name],
            imports=imports,
            declaration_order=tuple(order),
        )


# --- annotation parsing -----------------------------------------------------


@dataclass
class _AnnotationContext:
    """Bundle of name dictionaries the annotation walker reads.

    `nested_enum_values` is the one mutable slot -- struct() populates it with
    the current owner's nested enum constants before parsing its fields so an
    annotation like `bitset[Inner.MEMBER]` can resolve to an integer, and
    clears it afterward so the next struct sees a clean slate.
    """
    enum_names: frozenset[str]
    struct_names: frozenset[str]
    builtins: frozenset[str]
    aliases: dict[str, PrimitiveAlias | TypeAlias]
    nested_enum_values: dict[str, dict[str, int]] = dc_field(default_factory=dict)

    # ---- aliases -----------------------------------------------------------

    def parse_alias(
        self, name: str, value: griffe.Expr | str
    ) -> PrimitiveAlias | TypeAlias | None:
        if isinstance(value, griffe.ExprName) and value.name in PRIMITIVES:
            return PrimitiveAlias(name, value.name)
        target = self.type(name, value, None, frozenset())
        if target is None:
            return None
        return TypeAlias(name, target)

    # ---- declarations ------------------------------------------------------

    def enum(self, cls: griffe.Class) -> Enum:
        values: list[EnumValue] = []
        for name, attr in cls.attributes.items():
            if attr.value is None:
                continue
            parsed = self._enum_member_value(attr.value)
            if parsed is not None:
                values.append(EnumValue(name, *parsed))
        values = _resolve_sentinels(values)
        return Enum(cls.name, tuple(values), _decorator_int(cls, "type", "since"))

    def struct(self, cls: griffe.Class) -> Struct:
        nested_enums: list[Enum] = []
        nested_structs: list[Struct] = []
        for inner in cls.classes.values():
            if inner.is_alias:
                continue
            if _is_int_enum(inner):
                inner_enum = self.enum(inner)
                self._reject_versioned_nested(cls.name, inner_enum)
                nested_enums.append(inner_enum)
            else:
                self._reject_versioned_nested_struct(cls.name, inner)
                nested_structs.append(self.struct(inner))
        nested_names = frozenset(e.name for e in nested_enums)
        self.nested_enum_values = {
            e.name: {v.name: v.number for v in e.values}
            for e in nested_enums
        }
        try:
            fields: list[Field] = []
            earlier: set[str] = set()
            for attr in cls.attributes.values():
                f = self.field(attr, nested_names, frozenset(earlier))
                fields.append(f)
                earlier.add(f.name)
        finally:
            self.nested_enum_values = {}
        _check_trailing_is_last(cls.name, fields)
        since = _decorator_int(cls, "packet", "since")
        if since is None:
            since = _decorator_int(cls, "type", "since")
            if _decorator_int(cls, "type", "until") is not None:
                raise CompilerError(
                    f"{cls.name}: @type(until=) is only meaningful on a "
                    f"redeclared class -- a lone declaration cannot set until="
                )
        return Struct(
            name=cls.name,
            fields=tuple(fields),
            nested_enums=tuple(nested_enums),
            packet_id=_decorator_int(cls, "packet", "id"),
            since=since,
            deprecated=_decorator_int(cls, "type", "deprecated"),
            nested_structs=tuple(nested_structs),
        )

    def merged_struct(self, decls: list[griffe.Class]) -> Struct:
        name = decls[0].name
        versions: list[tuple[griffe.Class, int, int | None]] = []
        for cls in decls:
            if _is_int_enum(cls):
                raise CompilerError(
                    f"{name}: class redeclaration is supported for structs, not enums"
                )
            if _decorator_int(cls, "packet", "id") is not None:
                raise CompilerError(
                    f"{name}: redeclaration of a @packet class is unsupported"
                )
            if cls.classes:
                raise CompilerError(
                    f"{name}: a redeclared class cannot contain nested types"
                )
            since = _decorator_int(cls, "type", "since")
            if since is None:
                raise CompilerError(
                    f"{name}: every declaration of a redeclared class needs @type(since=)"
                )
            versions.append((cls, since, _decorator_int(cls, "type", "until")))
        versions.sort(key=lambda e: e[1])
        self._check_class_versions(name, versions)

        order: list[str] = []
        version_fields: list[dict[str, griffe.Attribute]] = []
        for cls, _, _ in versions:
            attrs = dict(cls.attributes)
            version_fields.append(attrs)
            for fname in attrs:
                if fname not in order:
                    order.append(fname)

        fields: list[Field] = []
        for i, fname in enumerate(order):
            earlier = frozenset(order[:i])
            version_list: list[FieldVersion] = []
            for (_, since, until), attrs in zip(versions, version_fields):
                attr = attrs.get(fname)
                if attr is None:
                    continue
                if attr.extra.get(extensions.EXTRA_NAMESPACE, {}).get(
                    extensions.REDECLARATIONS
                ):
                    raise CompilerError(
                        f"{name}.{fname}: a field cannot be version-redeclared "
                        f"inside a redeclared class"
                    )
                self._reject_field_version(name, attr)
                version = self._field_version(attr, frozenset(), earlier)
                version_list.append(replace(version, since=since, until=until))
            self._check_versions(fname, tuple(version_list))
            fields.append(Field(fname, tuple(version_list)))
        _check_trailing_is_last(name, fields)
        return Struct(
            name=name,
            fields=tuple(fields),
            nested_enums=(),
            packet_id=None,
            since=versions[0][1],
        )

    def field(
        self,
        attr: griffe.Attribute,
        nested: frozenset[str],
        earlier: frozenset[str],
    ) -> Field:
        decls = attr.extra.get(extensions.EXTRA_NAMESPACE, {}).get(
            extensions.REDECLARATIONS
        )
        sources: list[griffe.Attribute] = decls if decls is not None else [attr]
        versions = tuple(self._field_version(d, nested, earlier) for d in sources)
        self._check_versions(attr.name, versions)
        return Field(attr.name, versions)

    def _field_version(
        self,
        attr: griffe.Attribute,
        nested: frozenset[str],
        earlier: frozenset[str],
    ) -> FieldVersion:
        call = attr.value
        t = self.type(attr.name, attr.annotation, call, nested)
        count = _call_arg(call, "field", "count")
        if count is not None and t is not None:
            t = self._attach_count_expr(t, count, attr.name, call, nested, earlier)
        when = _call_arg(call, "field", "when")
        group_when = _call_arg(call, "field", "_group_when")
        if when is not None and group_when is not None:
            raise CompilerError(
                f"{attr.name}: a field inside a with field(when=...) guard "
                f"cannot also carry its own field(when=...)"
            )
        guard = when if when is not None else group_when
        if guard is not None:
            predicate = self._predicate(guard, attr.name, nested, earlier)
            if when is not None and isinstance(t, (OptionalType, VariantType)):
                raise CompilerError(
                    f"{attr.name}: field(when=...) gates a bare payload type -- "
                    f"it cannot also be an optional or union field"
                )
            if t is not None:
                t = CondType(
                    t, predicate, _int_kwarg(call, "field", "_group_id")
                )
        return FieldVersion(
            type=t,
            since=_int_kwarg(call, "field", "since"),
            until=_int_kwarg(call, "field", "until"),
        )

    def _attach_count_expr(
        self,
        t: FieldType,
        lam: _Ann,
        field_name: str,
        call: _Ann,
        nested: frozenset[str],
        earlier: frozenset[str],
    ) -> FieldType:
        if not isinstance(t, RepeatedType):
            raise CompilerError(
                f"{field_name}: field(count=...) only applies to a list[T] "
                f"field, got a non-list type"
            )
        if t.count is not None:
            raise CompilerError(
                f"{field_name}: field(count=...) is for variable-length lists; "
                f"a fixed-length tuple[T, ...] already carries its own count"
            )
        if _call_arg(call, "field", "prefix") is not None:
            raise CompilerError(
                f"{field_name}: field(count=...) and field(prefix=...) are "
                f"mutually exclusive -- a count-derived list has no length "
                f"prefix on the wire"
            )
        expr = self._predicate(lam, field_name, nested, earlier)
        return replace(t, count_expr=expr, prefix=None)

    # ---- field-type walker -------------------------------------------------

    def type(
        self, field_name: str, ann: _Ann, call: _Ann, nested: frozenset[str]
    ) -> FieldType | None:
        endian = _str_kwarg(call, "field", "endian")
        if endian is not None and endian not in ("big", "little"):
            raise CompilerError(
                f'{field_name}: field(endian=...) must be "big" or "little", got {endian!r}'
            )
        type_kw = _name_kwarg(call, "field", "type")
        if _is_none(_call_arg(call, "field", "prefix")):
            if not (isinstance(ann, griffe.ExprName) and ann.name == "bytes"):
                raise CompilerError(
                    f"{field_name}: field(prefix=None) marks a trailing payload "
                    f"and is only valid on a bare `bytes` field"
                )
            if endian is not None:
                raise CompilerError(_endian_scope_error(field_name))
            return PrimitiveType(name="bytes", trailing=True)
        prefix = self._repeat_prefix(call, field_name)
        tag = self._variant_tag(call, field_name)
        cases = _flatten_union(ann)
        if cases is not None:
            result = self._union_type(cases, field_name, type_kw, endian, prefix, nested, tag)
        else:
            base = self._base_type(ann, type_kw, prefix, nested, field_name, tag)
            if base is None:
                return None
            result = self._with_endian(base, endian, field_name)
        if tag is not None and not _has_variant(result):
            raise CompilerError(
                f"{field_name}: field(tag=...) sets a tagged-union discriminator "
                f"but the field's type tree contains no multi-case union"
            )
        return result

    def _union_type(
        self,
        cases: list[griffe.Expr | str],
        field_name: str,
        type_kw: str | None,
        endian: str | None,
        prefix: PrimitiveType,
        nested: frozenset[str],
        tag: _TagSpec | None = None,
    ) -> FieldType | None:
        if len(cases) == 2 and sum(_is_none(a) for a in cases) == 1:
            inner_ann = next(a for a in cases if not _is_none(a))
            base = self._base_type(inner_ann, type_kw, prefix, nested, field_name, tag)
            if base is None:
                return None
            if endian is not None:
                raise CompilerError(_endian_scope_error(field_name))
            discriminator = type_kw == "Union"
            if discriminator and isinstance(base, EnumType):
                raise CompilerError(
                    f"{field_name}: an optional enum field needs field(type=) for "
                    f"the enum wire primitive and so cannot also use type=Union"
                )
            present_tag = 1 if discriminator and _is_none(cases[0]) else 0
            return OptionalType(base, discriminator, present_tag)
        if endian is not None:
            raise CompilerError(_endian_scope_error(field_name))
        types: list[FieldType | None] = []
        for case in cases:
            if _is_none(case):
                types.append(None)
                continue
            t = self._base_type(case, type_kw, prefix, nested, field_name, tag)
            if t is None:
                return None
            types.append(t)
        if tag is None:
            return VariantType(tuple(types))
        return VariantType(
            tuple(types), discriminator=tag.primitive, tag_enum=tag.enum_name
        )

    def _base_type(
        self,
        ann: _Ann,
        type_kw: str | None,
        prefix: PrimitiveType,
        nested: frozenset[str],
        field_name: str,
        tag: _TagSpec | None = None,
    ) -> FieldType | None:
        if (builtin := self._builtin_of(ann)) is not None:
            return StructType(builtin)
        if isinstance(ann, griffe.ExprSubscript):
            bitset = self._bitset_parts(ann, field_name)
            if bitset is not None:
                return bitset
            repeat = _repeat_parts(ann, field_name)
            if repeat is not None:
                elem_ann, count = repeat
                inner = self._base_type(elem_ann, type_kw, prefix, nested, field_name, tag)
                if inner is None:
                    return None
                return RepeatedType(
                    inner=inner,
                    count=count,
                    prefix=prefix if count is None else None,
                )
            mapping = _map_parts(ann, field_name)
            if mapping is not None:
                key = self._base_type(mapping[0], type_kw, prefix, nested, field_name, tag)
                value = self._base_type(mapping[1], type_kw, prefix, nested, field_name, tag)
                if key is None or value is None:
                    return None
                return MappingType(key, value, prefix)
            return None
        cases = _flatten_union(ann)
        if cases is not None:
            return self._union_type(cases, field_name, type_kw, None, prefix, nested, tag)
        if isinstance(ann, griffe.ExprAttribute):
            # Dotted name `Parent.Child[.Grandchild...]` -- the resolver
            # recognises this as a nested struct reference when the full path
            # is in `struct_names`.
            parts = [str(v) for v in ann.values]
            dotted = ".".join(parts)
            if dotted in self.struct_names:
                return StructType(dotted)
            return None
        if not isinstance(ann, griffe.ExprName):
            return None
        name = ann.name
        if name in nested or name in self.enum_names:
            scalar = _enum_scalar(type_kw, field_name)
            if scalar is None and name in nested:
                raise CompilerError(
                    f"{field_name}: a nested enum cannot be string-coded "
                    f"(field(type=str)) -- use an integer wire primitive, or "
                    f"lift the enum to module scope"
                )
            return EnumType(name, scalar)
        if name in self.struct_names:
            return StructType(name)
        if name in PRIMITIVES:
            return PrimitiveType(name=name)
        alias = self.aliases.get(name)
        if isinstance(alias, PrimitiveAlias):
            return PrimitiveType(name=alias.primitive, alias=alias.name)
        if isinstance(alias, TypeAlias):
            target = alias.target
            if tag is not None and isinstance(target, VariantType):
                target = replace(
                    target,
                    discriminator=tag.primitive,
                    tag_enum=tag.enum_name,
                )
            return target
        return None

    def _variant_tag(self, call: _Ann, field_name: str) -> _TagSpec | None:
        """`field(tag=<integer primitive | IntEnum>)` overrides a `VariantType`'s
        on-wire discriminator. An enum tag names the C++ case labels but keeps
        the wire form as `varint32` (matching the BDS convention for tagged-
        union recipe / action enums). Absent kwarg -> leave the default
        (`uvarint32`)."""
        name = _name_kwarg(call, "field", "tag")
        if name is None:
            return None
        if name in INTEGER_PRIMITIVES:
            return _TagSpec(primitive=PrimitiveType(name=name))
        if name in self.enum_names:
            return _TagSpec(primitive=PrimitiveType(name="varint32"), enum_name=name)
        raise CompilerError(
            f"{field_name}: field(tag=...) must be an integer primitive or "
            f"a user-defined IntEnum, got {name!r}"
        )

    def _repeat_prefix(self, call: _Ann, field_name: str) -> PrimitiveType:
        name = _name_kwarg(call, "field", "prefix")
        if name is None:
            return PrimitiveType(name="uvarint32")
        if name not in INTEGER_PRIMITIVES:
            raise CompilerError(
                f"{field_name}: field(prefix=...) must be an integer primitive, got {name!r}"
            )
        return PrimitiveType(name=name)

    def _with_endian(
        self, base: FieldType, endian: str | None, field_name: str
    ) -> FieldType:
        if endian is None:
            return base
        big = endian == "big"
        if isinstance(base, PrimitiveType):
            return replace(base, big_endian=big)
        if (
            isinstance(base, EnumType)
            and base.scalar is not None
            and base.scalar.name not in VARINT_PRIMITIVES
        ):
            return replace(base, scalar=replace(base.scalar, big_endian=big))
        raise CompilerError(_endian_scope_error(field_name))

    # ---- predicates --------------------------------------------------------

    def _predicate(
        self,
        lam: _Ann,
        field_name: str,
        nested: frozenset[str],
        earlier: frozenset[str],
    ) -> Predicate:
        if not isinstance(lam, griffe.ExprLambda):
            raise CompilerError(
                f"{field_name}: field(when=...) must be a lambda predicate"
            )
        if len(lam.parameters) != 1:
            raise CompilerError(
                f"{field_name}: field(when=...) lambda takes exactly one parameter"
            )
        return self._pred_node(
            lam.body, lam.parameters[0].name, field_name, nested, earlier
        )

    def _pred_node(
        self,
        node: griffe.Expr | str,
        param: str,
        field_name: str,
        nested: frozenset[str],
        earlier: frozenset[str],
    ) -> Predicate:
        def child(n: griffe.Expr | str) -> Predicate:
            return self._pred_node(n, param, field_name, nested, earlier)

        if isinstance(node, griffe.ExprBoolOp):
            return Predicate(node.operator, operands=tuple(child(v) for v in node.values))
        if isinstance(node, griffe.ExprUnaryOp) and node.operator == "not":
            return Predicate("not", operands=(child(node.value),))
        if isinstance(node, griffe.ExprBinOp) and node.operator == "&":
            return Predicate("&", operands=(child(node.left), child(node.right)))
        if isinstance(node, griffe.ExprBinOp) and node.operator in ("*", "+", "-"):
            return Predicate(node.operator, operands=(child(node.left), child(node.right)))
        if isinstance(node, griffe.ExprCompare):
            if len(node.operators) != 1 or len(node.comparators) != 1:
                raise CompilerError(
                    f"{field_name}: field(when=...) supports one comparison per "
                    f"clause -- split a chained comparison with `and`"
                )
            op = str(node.operators[0])
            if op not in ("==", "!=", "<", ">", "<=", ">="):
                raise CompilerError(
                    f"{field_name}: field(when=...) comparison {op!r} is unsupported"
                )
            return Predicate(op, operands=(child(node.left), child(node.comparators[0])))
        if isinstance(node, griffe.ExprAttribute):
            return self._pred_attr(node, param, field_name, nested, earlier)
        if isinstance(node, griffe.ExprCall):
            return self._pred_call(node, param, field_name, nested, earlier)
        literal = _as_int(node)
        if literal is not None:
            return Predicate("int", text=str(literal))
        raise CompilerError(
            f"{field_name}: field(when=...) contains an unsupported expression: {node}"
        )

    def _pred_attr(
        self,
        node: griffe.ExprAttribute,
        param: str,
        field_name: str,
        nested: frozenset[str],
        earlier: frozenset[str],
    ) -> Predicate:
        parts = [str(v) for v in node.values]
        if len(parts) < 2:
            raise CompilerError(
                f"{field_name}: field(when=...) reference {'.'.join(parts)!r} is "
                f"too shallow -- use `param.field` or `Enum.MEMBER`"
            )
        head = parts[0]
        if head == param:
            top = parts[1]
            if top not in earlier:
                raise CompilerError(
                    f"{field_name}: field(when=...) references {top!r}, which is "
                    f"not a field declared before it"
                )
            return Predicate("field", text=".".join(parts[1:]))
        if len(parts) == 2 and (head in nested or head in self.enum_names):
            return Predicate("enum", text=f"{head}.{parts[1]}")
        raise CompilerError(
            f"{field_name}: field(when=...) reference {'.'.join(parts)!r} is "
            f"neither a `{param}.field[.sub...]` chain nor an Enum.MEMBER"
        )

    def _pred_call(
        self,
        node: griffe.ExprCall,
        param: str,
        field_name: str,
        nested: frozenset[str],
        earlier: frozenset[str],
    ) -> Predicate:
        """A `p.<field>.test(<int|Enum.MEMBER>)` bit-test on a bitset field."""
        receiver = node.function
        if not isinstance(receiver, griffe.ExprAttribute):
            raise CompilerError(
                f"{field_name}: field(when=...) call {node} is unsupported -- "
                f"only `p.<field>.test(<bit>)` is allowed"
            )
        parts = [str(v) for v in receiver.values]
        if len(parts) != 3 or parts[0] != param or parts[2] != "test":
            raise CompilerError(
                f"{field_name}: field(when=...) call must be of the form "
                f"`{param}.<earlier-field>.test(<bit>)`, got {receiver}"
            )
        target = parts[1]
        if target not in earlier:
            raise CompilerError(
                f"{field_name}: field(when=...) references {target!r}, which is "
                f"not a field declared before it"
            )
        args = [a for a in node.arguments if not isinstance(a, griffe.ExprKeyword)]
        if len(args) != 1:
            raise CompilerError(
                f"{field_name}: field(when=...) `.test(...)` takes exactly one "
                f"bit-index argument, got {len(args)}"
            )
        operand = self._pred_node(args[0], param, field_name, nested, earlier)
        if operand.kind not in ("int", "enum"):
            raise CompilerError(
                f"{field_name}: field(when=...) `.test(...)` argument must be an "
                f"integer literal or Enum.MEMBER, got {args[0]}"
            )
        return Predicate("bittest", text=target, operands=(operand,))

    def _bitset_parts(
        self, ann: griffe.ExprSubscript, field_name: str
    ) -> BitsetType | None:
        if not (
            isinstance(ann.left, griffe.ExprName) and ann.left.name == "bitset"
        ):
            return None
        size, enum_member = self._resolve_bitset_size(ann.slice)
        if size is None or size <= 0:
            raise CompilerError(
                f"{field_name}: bitset[...] needs a positive integer size -- "
                f"an int literal or a nested-enum member -- got {ann.slice!r}"
            )
        return BitsetType(size=size, enum_member=enum_member)

    def _resolve_bitset_size(
        self, expr: _Ann
    ) -> tuple[int | None, tuple[str, str] | None]:
        """Return the int width and, if the source was `Enum.MEMBER`, the
        symbolic ref so the resolver can re-resolve it per snapshot."""
        direct = _as_int(expr)
        if direct is not None:
            return direct, None
        if isinstance(expr, griffe.ExprAttribute):
            parts = [str(v) for v in expr.values]
            if len(parts) == 2:
                members = self.nested_enum_values.get(parts[0])
                if members is not None and parts[1] in members:
                    return members[parts[1]], (parts[0], parts[1])
        return None, None

    # ---- misc --------------------------------------------------------------

    def _builtin_of(self, ann: _Ann) -> str | None:
        if isinstance(ann, griffe.ExprName):
            if ann.name in self.builtins or ann.name == "UUID":
                return ann.name
            return None
        if isinstance(ann, griffe.ExprAttribute) and str(ann) == "uuid.UUID":
            return "UUID"
        return None

    def _enum_member_value(
        self, value: _Ann
    ) -> tuple[int, int | None, int | None, int | None, bool] | None:
        direct = _as_int(value)
        if direct is not None:
            return direct, None, None, None, False
        if not (
            isinstance(value, griffe.ExprCall)
            and isinstance(value.function, griffe.ExprName)
            and value.function.name == "value"
        ):
            return None
        sentinel = _bool_kwarg(value, "value", "sentinel")
        positionals = [
            a for a in value.arguments if not isinstance(a, griffe.ExprKeyword)
        ]
        if sentinel:
            # The number is filled in post-pass via _resolve_sentinels.
            ivalue = 0
        else:
            if not positionals:
                return None
            ivalue = _as_int(positionals[0])
            if ivalue is None:
                return None
        return (
            ivalue,
            _int_kwarg(value, "value", "since"),
            _int_kwarg(value, "value", "until"),
            _int_kwarg(value, "value", "deprecated"),
            sentinel,
        )

    # ---- structural checks -------------------------------------------------

    @staticmethod
    def _check_class_versions(
        name: str, versions: list[tuple[griffe.Class, int, int | None]]
    ) -> None:
        for i, (_, since, until) in enumerate(versions):
            last = i == len(versions) - 1
            if last:
                if until is not None:
                    raise CompilerError(
                        f"{name}: the last declaration of a redeclared class must "
                        f"not set @type(until=)"
                    )
                continue
            if until is None:
                raise CompilerError(
                    f"{name}: every declaration of a redeclared class but the last "
                    f"needs @type(until=)"
                )
            if until <= since:
                raise CompilerError(
                    f"{name}: @type(until=) must be greater than since="
                )
            if until != versions[i + 1][1]:
                raise CompilerError(
                    f"{name}: redeclared class version ranges must be contiguous "
                    f"-- each until= must equal the next since="
                )

    @staticmethod
    def _check_versions(name: str, versions: tuple[FieldVersion, ...]) -> None:
        covered_to = 0
        for i, version in enumerate(versions):
            lo = version.since or 0
            if lo < covered_to:
                raise CompilerError(
                    f"{name}: redeclared field versions overlap or are out of order "
                    f"-- each since= must be at least the previous until="
                )
            if i < len(versions) - 1 and version.until is None:
                raise CompilerError(
                    f"{name}: every redeclared field version but the last needs until="
                )
            if version.until is not None:
                if version.until <= lo:
                    raise CompilerError(
                        f"{name}: field version until= must be greater than since="
                    )
                covered_to = version.until

    @staticmethod
    def _reject_field_version(struct: str, attr: griffe.Attribute) -> None:
        if (
            _int_kwarg(attr.value, "field", "since") is not None
            or _int_kwarg(attr.value, "field", "until") is not None
        ):
            raise CompilerError(
                f"{struct}.{attr.name}: field(since=/until=) is not allowed inside "
                f"a redeclared class -- the class declarations carry the version range"
            )

    @staticmethod
    def _reject_versioned_nested(owner: str, enum: Enum) -> None:
        if enum.since is not None:
            raise CompilerError(
                f"{owner}.{enum.name}: a nested enum cannot carry @type(since=); "
                f"declare it at module scope to version it"
            )
        # Per-value `since=`/`until=` is allowed on nested enums. The nested
        # body emitted into the owner's first-snapshot definition carries every
        # member; the version gate is documentation that travels with the IR.

    @staticmethod
    def _reject_versioned_nested_struct(owner: str, cls: griffe.Class) -> None:
        """Nested struct types are scoped inside their parent and so cannot
        carry their own `@type(since=/until=/deprecated=)` or `@packet(...)`
        decorator. Versioning a nested type means lifting it to module scope."""
        for kw in ("since", "until", "deprecated"):
            if _decorator_int(cls, "type", kw) is not None:
                raise CompilerError(
                    f"{owner}.{cls.name}: a nested struct cannot carry "
                    f"@type({kw}=); declare it at module scope to version it"
                )
        if _decorator_int(cls, "packet", "id") is not None:
            raise CompilerError(
                f"{owner}.{cls.name}: a nested struct cannot be a @packet"
            )
        redecls = cls.extra.get(extensions.EXTRA_NAMESPACE, {}).get(
            extensions.CLASS_REDECLARATIONS
        )
        if redecls is not None:
            raise CompilerError(
                f"{owner}.{cls.name}: a nested struct cannot be redeclared "
                f"across version ranges; lift it to module scope"
            )


def _has_variant(t: FieldType | None) -> bool:
    """True iff the type tree contains a `VariantType` somewhere -- used to
    validate `field(tag=...)` actually has a target."""
    if t is None:
        return False
    if isinstance(t, VariantType):
        return True
    if isinstance(t, (OptionalType, RepeatedType, CondType)):
        return _has_variant(t.inner)
    if isinstance(t, MappingType):
        return _has_variant(t.key) or _has_variant(t.value)
    return False


def _is_trailing(t: FieldType | None) -> bool:
    """True iff the field is a trailing-bytes primitive (possibly wrapped in
    a CondType for `with field(when=...)`). The frame-consuming read leaves
    nothing for a following field, so this must be the last field."""
    while isinstance(t, CondType):
        t = t.inner
    return isinstance(t, PrimitiveType) and t.trailing


def _check_trailing_is_last(struct_name: str, fields: list[Field]) -> None:
    for i, f in enumerate(fields[:-1]):
        if any(_is_trailing(v.type) for v in f.versions):
            raise CompilerError(
                f"{struct_name}.{f.name}: a trailing field (bytes with "
                f"field(prefix=None)) must be the last field of the struct"
            )


def _resolve_sentinels(values: list[EnumValue]) -> list[EnumValue]:
    """Fill in the number of each `value(sentinel=True)` member as one past
    the highest non-sentinel member of the enum. If the enum has no concrete
    members, the sentinel is rejected -- there's nothing to count past."""
    non_sentinel = [v.number for v in values if not v.sentinel]
    if not any(v.sentinel for v in values):
        return values
    if not non_sentinel:
        sentinel = next(v for v in values if v.sentinel)
        raise CompilerError(
            f"{sentinel.name}: value(sentinel=True) needs at least one "
            f"non-sentinel member to count past"
        )
    high = max(non_sentinel) + 1
    return [replace(v, number=high) if v.sentinel else v for v in values]


# --- module-free helpers ------------------------------------------------------


def _package_of(mod: griffe.Module) -> str | None:
    attr = mod.attributes.get("package")
    if attr is None or attr.value is None:
        return None
    return str(attr.value).strip("'\"")


def _dsl_version(loaded: dict[str, griffe.Module]) -> int | None:
    """Pull `__version__` off any loaded module that declares it -- in
    practice the DSL surface module (`protocol/__init__.py`), which the
    schema files all import from. The single source for "what protocol
    version this project targets"; the CLI raises if it is missing."""
    for mod in loaded.values():
        attr = mod.attributes.get("__version__")
        if attr is None or attr.value is None:
            continue
        try:
            return int(str(attr.value))
        except ValueError:
            continue
    return None


def _is_int_enum(cls: griffe.Class) -> bool:
    return any(
        isinstance(b, griffe.ExprName) and b.name == "IntEnum" for b in cls.bases
    )


def _is_builtin_class(cls: griffe.Class) -> bool:
    return any(
        isinstance(dec.value, griffe.ExprName) and dec.value.name == "builtin"
        for dec in cls.decorators
    )


def _is_none(case: object) -> bool:
    """A literal `None` in source. griffe spells a keyword literal as the
    bare string `'None'` (vs `ExprName('Other')` for a name reference), so
    this also flags an explicit `field(prefix=None)`."""
    return case == "None"


def _as_int(value: object) -> int | None:
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    if isinstance(value, griffe.ExprUnaryOp) and value.operator == "-":
        inner = _as_int(value.value)
        return None if inner is None else -inner
    return None


def _flatten_union(ann: _Ann) -> list[griffe.Expr | str] | None:
    if not (isinstance(ann, griffe.ExprBinOp) and ann.operator == "|"):
        return None
    cases: list[griffe.Expr | str] = []
    stack: list[griffe.Expr | str] = [ann]
    while stack:
        node = stack.pop()
        if isinstance(node, griffe.ExprBinOp) and node.operator == "|":
            stack.append(node.right)
            stack.append(node.left)
        else:
            cases.append(node)
    return cases


def _repeat_parts(
    ann: griffe.ExprSubscript, field_name: str
) -> tuple[griffe.Expr | str, int | None] | None:
    if not isinstance(ann.left, griffe.ExprName):
        return None
    if ann.left.name == "list":
        return ann.slice, None
    if ann.left.name != "tuple":
        return None
    slice_ = ann.slice
    elements: list[griffe.Expr | str] = (
        list(slice_.elements) if isinstance(slice_, griffe.ExprTuple) else [slice_]
    )
    named = [e for e in elements if isinstance(e, griffe.ExprName)]
    if not named or len(named) != len(elements):
        raise CompilerError(
            f"{field_name}: tuple[...] must spell out a fixed count of named "
            f"element types -- use list[T] for a variable-length list"
        )
    if any(e.name != named[0].name for e in named):
        raise CompilerError(
            f"{field_name}: tuple[...] elements must all be the same type"
        )
    return named[0], len(named)




def _map_parts(
    ann: griffe.ExprSubscript, field_name: str
) -> tuple[griffe.Expr | str, griffe.Expr | str] | None:
    if not (isinstance(ann.left, griffe.ExprName) and ann.left.name == "dict"):
        return None
    slice_ = ann.slice
    if not isinstance(slice_, griffe.ExprTuple) or len(slice_.elements) != 2:
        raise CompilerError(
            f"{field_name}: dict[...] needs exactly a key type and a value type"
        )
    return slice_.elements[0], slice_.elements[1]


def _enum_scalar(type_kw: str | None, field_name: str) -> PrimitiveType | None:
    if type_kw is None:
        raise CompilerError(
            f"{field_name}: enum-typed field requires field(type=<primitive>) "
            f"-- e.g. type=uvarint32 or type=str"
        )
    if type_kw == "str":
        return None
    if type_kw not in PRIMITIVES:
        raise CompilerError(
            f"{field_name}: unknown wire primitive {type_kw!r}; valid: {sorted(PRIMITIVES)}"
        )
    return PrimitiveType(name=type_kw)


def _endian_scope_error(field_name: str) -> str:
    return (
        f"{field_name}: field(endian=...) only applies to fixed-width primitive "
        f"or fixed-width integer-coded enum fields"
    )


def _call_arg(expr: _Ann, fn_name: str, kw: str) -> _Ann:
    if not (
        isinstance(expr, griffe.ExprCall)
        and isinstance(expr.function, griffe.ExprName)
        and expr.function.name == fn_name
    ):
        return None
    for arg in expr.arguments:
        if isinstance(arg, griffe.ExprKeyword) and arg.name == kw:
            return arg.value
    return None


def _int_kwarg(expr: _Ann, fn_name: str, kw: str) -> int | None:
    return _as_int(_call_arg(expr, fn_name, kw))


def _bool_kwarg(expr: _Ann, fn_name: str, kw: str) -> bool:
    value = _call_arg(expr, fn_name, kw)
    if isinstance(value, str) and value == "True":
        return True
    if isinstance(value, griffe.ExprName) and value.name == "True":
        return True
    return False


def _name_kwarg(expr: _Ann, fn_name: str, kw: str) -> str | None:
    value = _call_arg(expr, fn_name, kw)
    return value.name if isinstance(value, griffe.ExprName) else None


def _str_kwarg(expr: _Ann, fn_name: str, kw: str) -> str | None:
    value = _call_arg(expr, fn_name, kw)
    if (
        isinstance(value, str)
        and len(value) >= 2
        and value[0] in "\"'"
        and value[-1] == value[0]
    ):
        return value[1:-1]
    return None


def _decorator_int(cls: griffe.Class, decorator: str, kwarg: str) -> int | None:
    for dec in cls.decorators:
        v = _int_kwarg(dec.value, decorator, kwarg)
        if v is not None:
            return v
    return None
