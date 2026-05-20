"""Frontend — `.py` DSL files to `FileDescriptor` instances.

Analog of protoc's `io::Tokenizer` + `compiler::Parser`. We use griffe to
statically parse the user's Python source — the DSL decorators
(`@packet`, `@type`, `field()`, `value()`) are no-ops at runtime, so griffe
never executes them, only reads them as AST.

A `SourceTree` follows `from X.Y import ...` references between modules so a
struct in one file can reference a type declared in another. Every file the
sourcetree loads becomes a `FileDescriptor` in the resulting `FileSet`;
files passed to `load_all()` are also listed as `outputs` so the CLI knows
which ones to emit.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterator, cast

import griffe

from ..descriptor import (
    INTEGER_PRIMITIVES,
    PRIMITIVES,
    VARINT_PRIMITIVES,
    CompilerError,
    CondWire,
    EnumDescriptor,
    EnumValueDescriptor,
    EnumWire,
    FieldDescriptor,
    FieldEraDescriptor,
    FileDescriptor,
    FileSet,
    MappingRef,
    MappingWire,
    NamedRef,
    OptionalRef,
    OptionalWire,
    Predicate,
    PrimitiveAliasDescriptor,
    PrimitiveRef,
    RepeatedRef,
    RepeatedWire,
    ScalarWire,
    StringWire,
    StructDescriptor,
    StructWire,
    SwitchWire,
    TypeAliasDescriptor,
    TypeRef,
    VariantRef,
    Wire,
)
from . import redeclaration

_Ann = griffe.Expr | str | None


@dataclass
class _ClassifyResult:
    """Output of the cross-module classification pass — immutable from
    `_lower_file`'s point of view, so no mid-pipeline mutation."""
    enum_names: frozenset[str]
    struct_names: frozenset[str]
    builtins: frozenset[str]
    aliases_by_name: dict[str, PrimitiveAliasDescriptor | TypeAliasDescriptor]
    primitive_aliases_by_module: dict[str, tuple[PrimitiveAliasDescriptor, ...]]
    type_aliases_by_module: dict[str, tuple[TypeAliasDescriptor, ...]]


class SourceTree:
    """Loads `.py` DSL files via griffe, lowers them to `FileDescriptor`.

    `import_paths` are the directories the loader uses to resolve `from X.Y
    import ...` references between modules — protoc's `--proto_path` equivalent.
    """

    def __init__(self, import_paths: list[Path]) -> None:
        self._import_paths = [p.resolve() for p in import_paths]
        # Shared across every griffe.load: keeps version-redeclared attributes
        # griffe's name-keyed mapping would otherwise collapse.
        self._extensions = griffe.Extensions(redeclaration.RedeclarationExtension())

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
                    candidate = ip.joinpath(*parts).with_suffix(".py")
                    if candidate.is_file():
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
        aliases_by_name: dict[str, PrimitiveAliasDescriptor | TypeAliasDescriptor] = {}
        primitive_aliases_by_module: dict[str, tuple[PrimitiveAliasDescriptor, ...]] = {}
        type_aliases_by_module: dict[str, tuple[TypeAliasDescriptor, ...]] = {}

        for mod in loaded.values():
            for cls in mod.classes.values():
                if cls.is_alias:
                    continue
                if _is_builtin_class(cls):
                    builtins.add(cls.name)
                    continue
                if _is_int_enum(cls):
                    enum_names.add(cls.name)
                else:
                    struct_names.add(cls.name)

        # Alias pass — must run after classification because an alias may
        # reference any class anywhere; within this pass declaration order
        # is the resolution order so an alias may reference an earlier one.
        for name, mod in loaded.items():
            primitives: list[PrimitiveAliasDescriptor] = []
            others: list[TypeAliasDescriptor] = []
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
                alias = ctx.parse_alias(attr_name, attr.value)
                if alias is None:
                    continue
                aliases_by_name[alias.name] = alias
                if isinstance(alias, PrimitiveAliasDescriptor):
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
    ) -> FileDescriptor:
        ctx = _AnnotationContext(
            enum_names=classified.enum_names,
            struct_names=classified.struct_names,
            builtins=classified.builtins,
            aliases=classified.aliases_by_name,
        )
        enums: list[EnumDescriptor] = []
        structs: list[StructDescriptor] = []
        order: list[str] = []
        for cls in mod.classes.values():
            if cls.is_alias or cls.name in classified.builtins:
                continue
            redecls = cls.extra.get(redeclaration.EXTRA_NAMESPACE, {}).get(
                redeclaration.CLASS_REDECLARATIONS
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
        return FileDescriptor(
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
    """Bundle of name dictionaries the annotation walker reads. Immutable
    after the classify pass — no `self.` mutation during lowering.
    """
    enum_names: frozenset[str]
    struct_names: frozenset[str]
    builtins: frozenset[str]
    aliases: dict[str, PrimitiveAliasDescriptor | TypeAliasDescriptor]

    # ---- aliases -----------------------------------------------------------

    def parse_alias(
        self, name: str, value: griffe.Expr | str
    ) -> PrimitiveAliasDescriptor | TypeAliasDescriptor | None:
        if isinstance(value, griffe.ExprName) and value.name in PRIMITIVES:
            return PrimitiveAliasDescriptor(name, value.name)
        type_ref = self.type_ref(value, name)
        wire = self.wire(name, value, None, frozenset())
        if type_ref is None or wire is None:
            return None
        return TypeAliasDescriptor(name, type_ref, wire)

    # ---- declarations ------------------------------------------------------

    def enum(self, cls: griffe.Class) -> EnumDescriptor:
        values: list[EnumValueDescriptor] = []
        for name, attr in cls.attributes.items():
            if attr.value is None:
                continue
            parsed = self._enum_member_value(attr.value)
            if parsed is not None:
                values.append(EnumValueDescriptor(name, *parsed))
        return EnumDescriptor(cls.name, tuple(values), _decorator_int(cls, "type", "since"))

    def struct(self, cls: griffe.Class) -> StructDescriptor:
        nested_enums: list[EnumDescriptor] = []
        for inner in cls.classes.values():
            if inner.is_alias or not _is_int_enum(inner):
                continue
            inner_enum = self.enum(inner)
            self._reject_versioned_nested(cls.name, inner_enum)
            nested_enums.append(inner_enum)
        nested_names = frozenset(e.name for e in nested_enums)
        fields: list[FieldDescriptor] = []
        earlier: set[str] = set()
        for attr in cls.attributes.values():
            f = self.field(attr, nested_names, frozenset(earlier))
            fields.append(f)
            earlier.add(f.name)
        since = _decorator_int(cls, "packet", "since")
        if since is None:
            since = _decorator_int(cls, "type", "since")
            if _decorator_int(cls, "type", "until") is not None:
                raise CompilerError(
                    f"{cls.name}: @type(until=) is only meaningful on a "
                    f"redeclared class -- a lone declaration cannot set until="
                )
        return StructDescriptor(
            name=cls.name,
            fields=tuple(fields),
            nested_enums=tuple(nested_enums),
            packet_id=_decorator_int(cls, "packet", "id"),
            since=since,
        )

    def merged_struct(self, decls: list[griffe.Class]) -> StructDescriptor:
        name = decls[0].name
        eras: list[tuple[griffe.Class, int, int | None]] = []
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
            eras.append((cls, since, _decorator_int(cls, "type", "until")))
        eras.sort(key=lambda e: e[1])
        self._check_class_eras(name, eras)

        order: list[str] = []
        era_fields: list[dict[str, griffe.Attribute]] = []
        for cls, _, _ in eras:
            attrs = dict(cls.attributes)
            era_fields.append(attrs)
            for fname in attrs:
                if fname not in order:
                    order.append(fname)

        fields: list[FieldDescriptor] = []
        for i, fname in enumerate(order):
            earlier = frozenset(order[:i])
            era_list: list[FieldEraDescriptor] = []
            for (_, since, until), attrs in zip(eras, era_fields):
                attr = attrs.get(fname)
                if attr is None:
                    continue
                if attr.extra.get(redeclaration.EXTRA_NAMESPACE, {}).get(
                    redeclaration.REDECLARATIONS
                ):
                    raise CompilerError(
                        f"{name}.{fname}: a field cannot be version-redeclared "
                        f"inside a redeclared class"
                    )
                self._reject_field_version(name, attr)
                era = self._field_era(attr, frozenset(), earlier)
                era_list.append(replace(era, since=since, until=until))
            self._check_eras(fname, tuple(era_list))
            fields.append(FieldDescriptor(fname, tuple(era_list)))
        return StructDescriptor(
            name=name,
            fields=tuple(fields),
            nested_enums=(),
            packet_id=None,
            since=eras[0][1],
        )

    def field(
        self,
        attr: griffe.Attribute,
        nested: frozenset[str],
        earlier: frozenset[str],
    ) -> FieldDescriptor:
        decls = attr.extra.get(redeclaration.EXTRA_NAMESPACE, {}).get(
            redeclaration.REDECLARATIONS
        )
        sources: list[griffe.Attribute] = decls if decls is not None else [attr]
        eras = tuple(self._field_era(d, nested, earlier) for d in sources)
        self._check_eras(attr.name, eras)
        return FieldDescriptor(attr.name, eras)

    def _field_era(
        self,
        attr: griffe.Attribute,
        nested: frozenset[str],
        earlier: frozenset[str],
    ) -> FieldEraDescriptor:
        call = attr.value
        type_ref = self.type_ref(attr.annotation, attr.name)
        wire = self.wire(attr.name, attr.annotation, call, nested)
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
            if when is not None and isinstance(wire, (OptionalWire, SwitchWire)):
                raise CompilerError(
                    f"{attr.name}: field(when=...) gates a bare payload type -- "
                    f"it cannot also be an optional or union field"
                )
            if wire is not None:
                wire = CondWire(
                    wire, predicate, _int_kwarg(call, "field", "_group_id")
                )
        return FieldEraDescriptor(
            type_ref=type_ref,
            wire=wire,
            since=_int_kwarg(call, "field", "since"),
            until=_int_kwarg(call, "field", "until"),
        )

    # ---- TypeRef walker ----------------------------------------------------

    def type_ref(self, ann: _Ann, field_name: str) -> TypeRef | None:
        if ann is None:
            return None
        if (builtin := self._builtin_of(ann)) is not None:
            return NamedRef(builtin)
        arms = _flatten_union(ann)
        if arms is not None:
            return self._union_type_ref(arms, field_name)
        if isinstance(ann, griffe.ExprSubscript):
            repeat = _repeat_parts(ann, field_name)
            if repeat is not None:
                elem_ann, count = repeat
                inner = self.type_ref(elem_ann, field_name)
                return RepeatedRef(inner, count) if inner is not None else None
            mapping = _map_parts(ann, field_name)
            if mapping is not None:
                key = self.type_ref(mapping[0], field_name)
                value = self.type_ref(mapping[1], field_name)
                if key is None or value is None:
                    return None
                return MappingRef(key, value)
            return None
        if isinstance(ann, griffe.ExprName):
            if ann.name in PRIMITIVES:
                return PrimitiveRef(name=ann.name)
            alias = self.aliases.get(ann.name)
            if isinstance(alias, TypeAliasDescriptor):
                return alias.target
            return NamedRef(ann.name)
        return None

    def _union_type_ref(
        self, arms: list[griffe.Expr | str], field_name: str
    ) -> TypeRef | None:
        if len(arms) == 2 and sum(_is_none(a) for a in arms) == 1:
            inner_ann = next(a for a in arms if not _is_none(a))
            inner = self.type_ref(inner_ann, field_name)
            return OptionalRef(inner) if inner is not None else None
        refs: list[TypeRef | None] = []
        for arm in arms:
            if _is_none(arm):
                refs.append(None)
                continue
            ref = self.type_ref(arm, field_name)
            if ref is None:
                return None
            refs.append(ref)
        return VariantRef(tuple(refs))

    # ---- Wire walker -------------------------------------------------------

    def wire(
        self, field_name: str, ann: _Ann, call: _Ann, nested: frozenset[str]
    ) -> Wire | None:
        endian = _str_kwarg(call, "field", "endian")
        if endian is not None and endian not in ("big", "little"):
            raise CompilerError(
                f'{field_name}: field(endian=...) must be "big" or "little", got {endian!r}'
            )
        type_kw = _name_kwarg(call, "field", "type")
        prefix = self._repeat_prefix(call, field_name)
        arms = _flatten_union(ann)
        if arms is not None:
            return self._union_wire(arms, field_name, type_kw, endian, prefix, nested)
        base = self._base_wire(ann, type_kw, prefix, nested, field_name)
        if base is None:
            return None
        return self._with_endian(base, endian, field_name)

    def _union_wire(
        self,
        arms: list[griffe.Expr | str],
        field_name: str,
        type_kw: str | None,
        endian: str | None,
        prefix: ScalarWire,
        nested: frozenset[str],
    ) -> Wire | None:
        if len(arms) == 2 and sum(_is_none(a) for a in arms) == 1:
            inner_ann = next(a for a in arms if not _is_none(a))
            base = self._base_wire(inner_ann, type_kw, prefix, nested, field_name)
            if base is None:
                return None
            if endian is not None:
                raise CompilerError(_endian_scope_error(field_name))
            discriminator = type_kw == "Union"
            if discriminator and isinstance(base, EnumWire):
                raise CompilerError(
                    f"{field_name}: an optional enum field needs field(type=) for "
                    f"the enum wire primitive and so cannot also use type=Union"
                )
            present_tag = 1 if discriminator and _is_none(arms[0]) else 0
            return OptionalWire(base, discriminator, present_tag)
        if endian is not None:
            raise CompilerError(_endian_scope_error(field_name))
        wires: list[Wire | None] = []
        for arm in arms:
            if _is_none(arm):
                wires.append(None)
                continue
            w = self._base_wire(arm, type_kw, prefix, nested, field_name)
            if w is None:
                return None
            wires.append(w)
        return SwitchWire(tuple(wires))

    def _base_wire(
        self,
        ann: _Ann,
        type_kw: str | None,
        prefix: ScalarWire,
        nested: frozenset[str],
        field_name: str,
    ) -> Wire | None:
        if (builtin := self._builtin_of(ann)) is not None:
            return StructWire(builtin)
        if isinstance(ann, griffe.ExprSubscript):
            repeat = _repeat_parts(ann, field_name)
            if repeat is not None:
                elem_ann, count = repeat
                inner = self._base_wire(elem_ann, type_kw, prefix, nested, field_name)
                if inner is None:
                    return None
                return RepeatedWire(inner, prefix if count is None else None, count)
            mapping = _map_parts(ann, field_name)
            if mapping is not None:
                key = self._base_wire(mapping[0], type_kw, prefix, nested, field_name)
                value = self._base_wire(mapping[1], type_kw, prefix, nested, field_name)
                if key is None or value is None:
                    return None
                return MappingWire(key, value, prefix)
            return None
        if not isinstance(ann, griffe.ExprName):
            return None
        name = ann.name
        if name in nested or name in self.enum_names:
            scalar = _enum_wire(type_kw, field_name)
            if scalar is None and name in nested:
                raise CompilerError(
                    f"{field_name}: a nested enum cannot be string-coded "
                    f"(field(type=str)) -- use an integer wire primitive, or "
                    f"lift the enum to module scope"
                )
            return EnumWire(name, scalar)
        if name in self.struct_names:
            return StructWire(name)
        if name in ("str", "bytes"):
            return StringWire()
        if name in PRIMITIVES:
            return ScalarWire(name, varint=name in VARINT_PRIMITIVES)
        alias = self.aliases.get(name)
        if isinstance(alias, PrimitiveAliasDescriptor):
            return ScalarWire(alias.primitive, varint=alias.primitive in VARINT_PRIMITIVES)
        if isinstance(alias, TypeAliasDescriptor):
            return alias.wire
        return None

    def _repeat_prefix(self, call: _Ann, field_name: str) -> ScalarWire:
        name = _name_kwarg(call, "field", "prefix")
        if name is None:
            return ScalarWire("uvarint32", varint=True)
        if name not in INTEGER_PRIMITIVES:
            raise CompilerError(
                f"{field_name}: field(prefix=...) must be an integer primitive, got {name!r}"
            )
        return ScalarWire(name, varint=name in VARINT_PRIMITIVES)

    def _with_endian(self, base: Wire, endian: str | None, field_name: str) -> Wire:
        if endian is None:
            return base
        big = endian == "big"
        if isinstance(base, ScalarWire):
            return replace(base, big_endian=big)
        if isinstance(base, EnumWire) and base.scalar is not None and not base.scalar.varint:
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
        if len(parts) != 2:
            raise CompilerError(
                f"{field_name}: field(when=...) reference {'.'.join(parts)!r} is "
                f"too deep -- use `param.field` or `Enum.MEMBER`"
            )
        head, tail = parts
        if head == param:
            if tail not in earlier:
                raise CompilerError(
                    f"{field_name}: field(when=...) references {tail!r}, which is "
                    f"not a field declared before it"
                )
            return Predicate("field", text=tail)
        if head in nested or head in self.enum_names:
            return Predicate("enum", text=f"{head}.{tail}")
        raise CompilerError(
            f"{field_name}: field(when=...) reference {head!r} is neither the "
            f"lambda parameter nor a known enum"
        )

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
    ) -> tuple[int, int | None, int | None] | None:
        direct = _as_int(value)
        if direct is not None:
            return direct, None, None
        if not (
            isinstance(value, griffe.ExprCall)
            and isinstance(value.function, griffe.ExprName)
            and value.function.name == "value"
            and value.arguments
        ):
            return None
        ivalue = _as_int(value.arguments[0])
        if ivalue is None:
            return None
        return (
            ivalue,
            _int_kwarg(value, "value", "since"),
            _int_kwarg(value, "value", "until"),
        )

    # ---- structural checks -------------------------------------------------

    @staticmethod
    def _check_class_eras(
        name: str, eras: list[tuple[griffe.Class, int, int | None]]
    ) -> None:
        for i, (_, since, until) in enumerate(eras):
            last = i == len(eras) - 1
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
            if until != eras[i + 1][1]:
                raise CompilerError(
                    f"{name}: redeclared class version ranges must be contiguous "
                    f"-- each until= must equal the next since="
                )

    @staticmethod
    def _check_eras(name: str, eras: tuple[FieldEraDescriptor, ...]) -> None:
        covered_to = 0
        for i, era in enumerate(eras):
            lo = era.since or 0
            if lo < covered_to:
                raise CompilerError(
                    f"{name}: redeclared field eras overlap or are out of order "
                    f"-- each since= must be at least the previous until="
                )
            if i < len(eras) - 1 and era.until is None:
                raise CompilerError(
                    f"{name}: every redeclared field era but the last needs until="
                )
            if era.until is not None:
                if era.until <= lo:
                    raise CompilerError(
                        f"{name}: field era until= must be greater than since="
                    )
                covered_to = era.until

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
    def _reject_versioned_nested(owner: str, enum: EnumDescriptor) -> None:
        if enum.since is not None:
            raise CompilerError(
                f"{owner}.{enum.name}: a nested enum cannot carry @type(since=); "
                f"declare it at module scope to version it"
            )
        for v in enum.values:
            if v.since is not None or v.until is not None:
                raise CompilerError(
                    f"{owner}.{enum.name}.{v.name}: a nested enum cannot have "
                    f"version-gated members; declare it at module scope to version it"
                )


# --- module-free helpers ------------------------------------------------------


def _package_of(mod: griffe.Module) -> str | None:
    attr = mod.attributes.get("package")
    if attr is None or attr.value is None:
        return None
    return str(attr.value).strip("'\"")


def _is_int_enum(cls: griffe.Class) -> bool:
    return any(
        isinstance(b, griffe.ExprName) and b.name == "IntEnum" for b in cls.bases
    )


def _is_builtin_class(cls: griffe.Class) -> bool:
    return any(
        isinstance(dec.value, griffe.ExprName) and dec.value.name == "builtin"
        for dec in cls.decorators
    )


def _is_none(arm: object) -> bool:
    return arm == "None"


def _as_int(value: object) -> int | None:
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _flatten_union(ann: _Ann) -> list[griffe.Expr | str] | None:
    if not (isinstance(ann, griffe.ExprBinOp) and ann.operator == "|"):
        return None
    arms: list[griffe.Expr | str] = []
    stack: list[griffe.Expr | str] = [ann]
    while stack:
        node = stack.pop()
        if isinstance(node, griffe.ExprBinOp) and node.operator == "|":
            stack.append(node.right)
            stack.append(node.left)
        else:
            arms.append(node)
    return arms


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


def _enum_wire(type_kw: str | None, field_name: str) -> ScalarWire | None:
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
    return ScalarWire(type_kw, varint=type_kw in VARINT_PRIMITIVES)


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
