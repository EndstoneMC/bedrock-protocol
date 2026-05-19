"""griffe frontend: load DSL modules and lower them to the language-agnostic
`schema` IR. Every griffe-specific concern -- module loading, import following,
`Expr` parsing -- is confined to this class.
"""

from dataclasses import replace
from pathlib import Path
from typing import cast

import griffe

from .redeclaration import (
    CLASS_REDECLARATIONS,
    EXTRA_NAMESPACE,
    REDECLARATIONS,
    RedeclarationExtension,
)
from .schema import (
    PRIMITIVES,
    VARINT_PRIMITIVES,
    Alias,
    CompilerError,
    Cond,
    Enum,
    EnumMember,
    EnumRef,
    Field,
    FieldArm,
    Map,
    Mapping,
    Module,
    Named,
    Opt,
    Optional,
    Pred,
    Primitive,
    Repeat,
    Repeated,
    Scalar,
    Schema,
    Str,
    Struct,
    StructRef,
    Switch,
    TypeRef,
    Variant,
    Wire,
)

#: An annotation, decorator argument, or literal as griffe surfaces it: an
#: expression node, a raw-source literal string, or absent.
_Ann = griffe.Expr | str | None


class Frontend:
    def __init__(self, import_paths: list[Path]):
        self._import_paths = import_paths

    def load(self, inputs: tuple[Path, ...]) -> Schema:
        self._griffe: dict[str, griffe.Module] = {}
        self._stems: dict[str, str] = {}
        # One extension instance, shared across every `griffe.load`: it keeps
        # version-redeclared class attributes that griffe would collapse.
        self._extensions = griffe.Extensions(RedeclarationExtension())
        outputs: list[str] = []
        for inp in inputs:
            name, root = self._module_name_and_root(inp)
            self._griffe[name] = cast(
                griffe.Module,
                griffe.load(
                    name,
                    search_paths=[str(root)],
                    allow_inspection=False,
                    extensions=self._extensions,
                ),
            )
            self._stems[name] = inp.stem
            outputs.append(name)
        self._follow_imports(outputs)
        self._classify()
        modules = {name: self._module(name) for name in self._griffe}
        return Schema(modules, tuple(outputs), frozenset(self._builtins))

    # --- module loading ------------------------------------------------------

    def _follow_imports(self, roots: list[str]) -> None:
        """Load modules referenced by `from X.Y import ...` so their types are
        resolvable. Imported-only modules supply context but produce no output."""
        pending = list(roots)
        while pending:
            for dep in self._imports_of(self._griffe[pending.pop()]):
                if dep in self._griffe:
                    continue
                parts = dep.split(".")
                for ip in self._import_paths:
                    candidate = ip.joinpath(*parts).with_suffix(".py")
                    if candidate.is_file():
                        self._griffe[dep] = cast(
                            griffe.Module,
                            griffe.load(
                                dep,
                                search_paths=[str(ip)],
                                allow_inspection=False,
                                extensions=self._extensions,
                            ),
                        )
                        pending.append(dep)
                        break

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

    @staticmethod
    def _imports_of(mod: griffe.Module) -> set[str]:
        """Dotted source modules behind this module's `from X.Y import ...`
        bindings. Modules with a `_`-prefixed component (the DSL itself) are
        omitted: they have no header to emit or include."""
        out: set[str] = set()
        for member in mod.members.values():
            target = getattr(member, "target_path", None)
            if target is None or "." not in str(target):
                continue
            dep = str(target).rsplit(".", 1)[0]
            if not any(part.startswith("_") for part in dep.split(".")):
                out.add(dep)
        return out

    # --- type classification (spans every loaded module) ---------------------

    def _classify(self) -> None:
        self._enum_names: set[str] = set()
        self._struct_names: set[str] = set()
        self._builtins: set[str] = set()
        self._alias_primitive: dict[str, str] = {}
        for mod in self._griffe.values():
            for cls in mod.classes.values():
                if cls.is_alias:
                    continue
                if self._is_builtin(cls):
                    self._builtins.add(cls.name)
                    continue
                bucket = self._enum_names if self._is_int_enum(cls) else self._struct_names
                bucket.add(cls.name)
            for alias in self._aliases(mod):
                self._alias_primitive[alias.name] = alias.primitive

    # --- module lowering -----------------------------------------------------

    def _module(self, name: str) -> Module:
        mod = self._griffe[name]
        types: list[Enum | Struct] = []
        for cls in mod.classes.values():
            if cls.is_alias or cls.name in self._builtins:
                continue
            redecls = cls.extra.get(EXTRA_NAMESPACE, {}).get(CLASS_REDECLARATIONS)
            if redecls is not None:
                types.append(self._merged_struct(redecls))
            elif self._is_int_enum(cls):
                types.append(self._enum(cls))
            else:
                types.append(self._struct(cls))
        imports = tuple(
            sorted(d for d in self._imports_of(mod) if d in self._griffe and d != name)
        )
        return Module(
            name, self._stems.get(name, name), self._package(mod),
            tuple(types), self._aliases(mod), imports,
        )

    @staticmethod
    def _package(mod: griffe.Module) -> str | None:
        attr = mod.attributes.get("package")
        if attr is None or attr.value is None:
            return None
        return str(attr.value).strip("'\"")

    def _aliases(self, mod: griffe.Module) -> tuple[Alias, ...]:
        """`Name = <primitive>` and PEP 695 `type Name = <primitive>`, skipping
        names that are themselves built-in primitives."""
        out: list[Alias] = []
        sources = list(mod.attributes.items()) + list(mod.type_aliases.items())
        for name, attr in sources:
            if name == "package" or name in PRIMITIVES or attr.value is None:
                continue
            if isinstance(attr.value, griffe.ExprName) and attr.value.name in PRIMITIVES:
                out.append(Alias(name, attr.value.name))
        return tuple(out)

    def _enum(self, cls: griffe.Class) -> Enum:
        members: list[EnumMember] = []
        for name, attr in cls.attributes.items():
            if attr.value is None:
                continue
            parsed = self._member_value(attr.value)
            if parsed is not None:
                members.append(EnumMember(name, *parsed))
        return Enum(cls.name, tuple(members), self._class_since(cls))

    def _struct(self, cls: griffe.Class) -> Struct:
        nested: list[Enum] = []
        for inner in cls.classes.values():
            if inner.is_alias or not self._is_int_enum(inner):
                continue
            enum = self._enum(inner)
            self._reject_versioned_nested(cls.name, enum)
            nested.append(enum)
        nested_names = frozenset(e.name for e in nested)
        fields_list: list[Field] = []
        earlier: set[str] = set()
        for attr in cls.attributes.values():
            field = self._field(attr, nested_names, frozenset(earlier))
            fields_list.append(field)
            earlier.add(field.name)
        fields = tuple(fields_list)
        since = self._packet_since(cls)
        if since is None:  # a non-packet struct version-gates via @type(since=)
            since = self._class_since(cls)
            if self._class_until(cls) is not None:
                raise CompilerError(
                    f"{cls.name}: @type(until=) is only meaningful on a "
                    f"redeclared class -- a lone declaration cannot set until="
                )
        return Struct(
            cls.name, fields, tuple(nested), self._packet_id(cls), since,
        )

    def _merged_struct(self, decls: list[griffe.Class]) -> Struct:
        """Lower a class redeclared once per protocol era -- each declaration
        carrying a `[since, until)` range via `@type` -- into one `Struct`
        whose fields carry version arms. Same-named fields across declarations
        merge into a multi-arm field; a field unique to one era is a single-arm
        field over that era's range."""
        name = decls[0].name
        # (class declaration, since, until), ordered by since.
        eras: list[tuple[griffe.Class, int, int | None]] = []
        for cls in decls:
            if self._is_int_enum(cls):
                raise CompilerError(
                    f"{name}: class redeclaration is supported for structs, "
                    f"not enums"
                )
            if self._packet_id(cls) is not None:
                raise CompilerError(
                    f"{name}: redeclaration of a @packet class is unsupported"
                )
            if cls.classes:
                raise CompilerError(
                    f"{name}: a redeclared class cannot contain nested types"
                )
            since = self._class_since(cls)
            if since is None:
                raise CompilerError(
                    f"{name}: every declaration of a redeclared class needs "
                    f"@type(since=)"
                )
            eras.append((cls, since, self._class_until(cls)))
        eras.sort(key=lambda e: e[1])
        self._check_class_eras(name, eras)

        # Merged field order: first appearance across the declarations.
        order: list[str] = []
        era_fields: list[dict[str, griffe.Attribute]] = []
        for cls, _, _ in eras:
            attrs = dict(cls.attributes)
            era_fields.append(attrs)
            for fname in attrs:
                if fname not in order:
                    order.append(fname)

        fields: list[Field] = []
        for i, fname in enumerate(order):
            earlier = frozenset(order[:i])
            arms: list[FieldArm] = []
            for (_, since, until), attrs in zip(eras, era_fields):
                attr = attrs.get(fname)
                if attr is None:
                    continue
                if attr.extra.get(EXTRA_NAMESPACE, {}).get(REDECLARATIONS):
                    raise CompilerError(
                        f"{name}.{fname}: a field cannot be version-redeclared "
                        f"inside a redeclared class -- the class declarations "
                        f"carry the version range"
                    )
                self._reject_field_version(name, attr)
                arm = self._arm(attr, frozenset(), earlier)
                arms.append(replace(arm, since=since, until=until))
            self._check_arms(fname, tuple(arms))
            fields.append(Field(fname, tuple(arms)))
        return Struct(name, tuple(fields), (), None, eras[0][1])

    @staticmethod
    def _check_class_eras(
        name: str, eras: list[tuple[griffe.Class, int, int | None]]
    ) -> None:
        """A redeclared class's eras run in ascending, contiguous `[since,
        until)` order; every era but the last is bounded by `until=`, and that
        `until=` is the next era's `since=`."""
        for i, (_, since, until) in enumerate(eras):
            last = i == len(eras) - 1
            if last:
                if until is not None:
                    raise CompilerError(
                        f"{name}: the last declaration of a redeclared class "
                        f"must not set @type(until=)"
                    )
                continue
            if until is None:
                raise CompilerError(
                    f"{name}: every declaration of a redeclared class but the "
                    f"last needs @type(until=)"
                )
            if until <= since:
                raise CompilerError(
                    f"{name}: @type(until=) must be greater than since="
                )
            if until != eras[i + 1][1]:
                raise CompilerError(
                    f"{name}: redeclared class version ranges must be "
                    f"contiguous -- each until= must equal the next since="
                )

    def _reject_field_version(self, struct: str, attr: griffe.Attribute) -> None:
        """A field inside a redeclared class draws its range from the class
        declarations, so it may not carry its own `field(since=/until=)`."""
        call = attr.value
        if call is None:
            return
        if (
            self._int_kwarg(call, "field", "since") is not None
            or self._int_kwarg(call, "field", "until") is not None
        ):
            raise CompilerError(
                f"{struct}.{attr.name}: field(since=/until=) is not allowed "
                f"inside a redeclared class -- the class declarations carry "
                f"the version range"
            )

    @staticmethod
    def _reject_versioned_nested(owner: str, enum: Enum) -> None:
        """A nested enum's member set is the owning packet's -- it has no
        version axis of its own. Version such an enum at module scope."""
        if enum.since is not None:
            raise CompilerError(
                f"{owner}.{enum.name}: a nested enum cannot carry @type(since=); "
                f"declare it at module scope to version it"
            )
        for m in enum.members:
            if m.since is not None or m.until is not None:
                raise CompilerError(
                    f"{owner}.{enum.name}.{m.name}: a nested enum cannot have "
                    f"version-gated members; declare it at module scope to version it"
                )

    def _field(
        self, attr: griffe.Attribute, nested: frozenset[str], earlier: frozenset[str]
    ) -> Field:
        """One field, built from `attr` -- or, when `attr` was redeclared once
        per protocol era, from the ordered list the redeclaration extension
        stashed on it. Each declaration becomes one version arm."""
        decls = attr.extra.get(EXTRA_NAMESPACE, {}).get(REDECLARATIONS)
        sources: list[griffe.Attribute] = decls if decls is not None else [attr]
        arms = tuple(self._arm(d, nested, earlier) for d in sources)
        self._check_arms(attr.name, arms)
        return Field(attr.name, arms)

    def _arm(
        self, attr: griffe.Attribute, nested: frozenset[str], earlier: frozenset[str]
    ) -> FieldArm:
        call = attr.value
        since = self._int_kwarg(call, "field", "since") if call is not None else None
        until = self._int_kwarg(call, "field", "until") if call is not None else None
        type_ref = self._typeref(attr.annotation, attr.name)
        wire = self._wire(attr.name, attr.annotation, call, nested)
        when = self._call_arg(call, "field", "when") if call is not None else None
        # `_group_when` is injected by the redeclaration extension when a field
        # is hoisted out of a `with field(when=...)` guard block. Unlike a
        # direct field(when=), a group guard may legitimately wrap an optional
        # or union field -- the guard gates the region, the optional flags the
        # field within it.
        group_when = (
            self._call_arg(call, "field", "_group_when") if call is not None else None
        )
        if when is not None and group_when is not None:
            raise CompilerError(
                f"{attr.name}: a field inside a with field(when=...) guard "
                f"cannot also carry its own field(when=...)"
            )
        guard = when if when is not None else group_when
        if guard is not None:
            predicate = self._predicate(guard, attr.name, nested, earlier)
            if when is not None and isinstance(wire, (Opt, Switch)):
                raise CompilerError(
                    f"{attr.name}: field(when=...) gates a bare payload type -- it "
                    f"cannot also be an optional or union field"
                )
            if wire is not None:
                wire = Cond(wire, predicate)
            # A value-gated field stays plain `T`: presence is recomputed from
            # the predicate, so an optional wrapper would be redundant.
        return FieldArm(type_ref, wire, since, until)

    @staticmethod
    def _check_arms(name: str, arms: tuple[FieldArm, ...]) -> None:
        """Version arms run in ascending, non-overlapping `[since, until)`
        order; every arm but the last is bounded by `until=`."""
        covered_to = 0
        for i, arm in enumerate(arms):
            lo = arm.since or 0
            if lo < covered_to:
                raise CompilerError(
                    f"{name}: redeclared field arms overlap or are out of order "
                    f"-- each since= must be at least the previous until="
                )
            if i < len(arms) - 1 and arm.until is None:
                raise CompilerError(
                    f"{name}: every redeclared field arm but the last needs until="
                )
            if arm.until is not None:
                if arm.until <= lo:
                    raise CompilerError(
                        f"{name}: field arm until= must be greater than since="
                    )
                covered_to = arm.until

    # --- type references -----------------------------------------------------

    def _typeref(self, ann: _Ann, field_name: str) -> TypeRef | None:
        if ann is None:
            return None
        if (builtin := self._builtin(ann)) is not None:
            return Named(builtin)
        arms = self._flatten_union(ann)
        if arms is not None:
            return self._union_typeref(arms, field_name)
        if isinstance(ann, griffe.ExprSubscript):
            repeat = self._repeat_parts(ann, field_name)
            if repeat is not None:
                elem_ann, count = repeat
                inner = self._typeref(elem_ann, field_name)
                return Repeated(inner, count) if inner is not None else None
            mapping = self._map_parts(ann, field_name)
            if mapping is not None:
                key = self._typeref(mapping[0], field_name)
                value = self._typeref(mapping[1], field_name)
                if key is None or value is None:
                    return None
                return Mapping(key, value)
            return None
        if isinstance(ann, griffe.ExprName):
            return Primitive(ann.name) if ann.name in PRIMITIVES else Named(ann.name)
        return None

    def _union_typeref(
        self, arms: list[griffe.Expr | str], field_name: str
    ) -> TypeRef | None:
        """`X | None` is an Optional; any other union is an N-arm Variant."""
        if len(arms) == 2 and sum(self._is_none(a) for a in arms) == 1:
            inner_ann = next(a for a in arms if not self._is_none(a))
            inner = self._typeref(inner_ann, field_name)
            return Optional(inner) if inner is not None else None
        refs: list[TypeRef | None] = []
        for arm in arms:
            if self._is_none(arm):
                refs.append(None)
                continue
            ref = self._typeref(arm, field_name)
            if ref is None:
                return None
            refs.append(ref)
        return Variant(tuple(refs))

    # --- wire encodings ------------------------------------------------------

    def _wire(
        self, field_name: str, ann: _Ann, call: _Ann, nested: frozenset[str]
    ) -> Wire | None:
        endian = self._str_kwarg(call, "field", "endian") if call is not None else None
        if endian is not None and endian not in ("big", "little"):
            raise CompilerError(
                f'{field_name}: field(endian=...) must be "big" or "little", '
                f"got {endian!r}"
            )
        type_kw = self._name_kwarg(call, "field", "type") if call is not None else None
        prefix = self._repeat_prefix(call, field_name)
        arms = self._flatten_union(ann)
        if arms is not None:
            return self._union_wire(
                arms, field_name, type_kw, endian, prefix, nested
            )
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
        prefix: Scalar,
        nested: frozenset[str],
    ) -> Wire | None:
        """`X | None` is an Optional (bool flag, or a union index under
        field(type=Union)); any other union is an N-arm varint-tagged Switch."""
        if len(arms) == 2 and sum(self._is_none(a) for a in arms) == 1:
            inner_ann = next(a for a in arms if not self._is_none(a))
            base = self._base_wire(inner_ann, type_kw, prefix, nested, field_name)
            if base is None:
                return None
            if endian is not None:
                raise CompilerError(self._endian_scope_error(field_name))
            discriminator = type_kw == "Union"
            if discriminator and isinstance(base, EnumRef):
                raise CompilerError(
                    f"{field_name}: an optional enum field needs field(type=) for "
                    f"the enum wire primitive and so cannot also use type=Union"
                )
            present_tag = 1 if discriminator and self._is_none(arms[0]) else 0
            return Opt(base, discriminator, present_tag)
        if endian is not None:
            raise CompilerError(self._endian_scope_error(field_name))
        wires: list[Wire | None] = []
        for arm in arms:
            if self._is_none(arm):
                wires.append(None)
                continue
            wire = self._base_wire(arm, type_kw, prefix, nested, field_name)
            if wire is None:
                return None
            wires.append(wire)
        return Switch(tuple(wires))

    def _repeat_prefix(self, call: _Ann, field_name: str) -> Scalar:
        """The length-prefix scalar a `list[T]` field uses -- `field(prefix=)`
        or the `uvarint32` default. Ignored by fixed-length `tuple` fields."""
        name = (
            self._name_kwarg(call, "field", "prefix") if call is not None else None
        )
        if name is None:
            return Scalar("uvarint32", varint=True)
        if name not in PRIMITIVES or name in (
            "str", "bytes", "bool", "float", "double",
        ):
            raise CompilerError(
                f"{field_name}: field(prefix=...) must be an integer primitive, "
                f"got {name!r}"
            )
        return Scalar(name, varint=name in VARINT_PRIMITIVES)

    def _repeat_parts(
        self, ann: griffe.ExprSubscript, field_name: str
    ) -> tuple[griffe.Expr | str, int | None] | None:
        """Classify a `list[T]` / `tuple[T, ...]` subscript into (element
        annotation, count) -- count None for a length-prefixed `list`, the
        element total for a fixed-length `tuple` -- or None for any other
        subscript. Rejects heterogeneous or variable-length tuples."""
        if not isinstance(ann.left, griffe.ExprName):
            return None
        if ann.left.name == "list":
            return ann.slice, None
        if ann.left.name != "tuple":
            return None
        slice_ = ann.slice
        elements: list[griffe.Expr | str] = (
            list(slice_.elements)
            if isinstance(slice_, griffe.ExprTuple)
            else [slice_]
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
        self, ann: griffe.ExprSubscript, field_name: str
    ) -> tuple[griffe.Expr | str, griffe.Expr | str] | None:
        """The (key, value) annotations of a `dict[K, V]` subscript, or None
        for any other subscript."""
        if not (isinstance(ann.left, griffe.ExprName) and ann.left.name == "dict"):
            return None
        slice_ = ann.slice
        if not isinstance(slice_, griffe.ExprTuple) or len(slice_.elements) != 2:
            raise CompilerError(
                f"{field_name}: dict[...] needs exactly a key type and a value type"
            )
        return slice_.elements[0], slice_.elements[1]

    def _base_wire(
        self,
        ann: _Ann,
        type_kw: str | None,
        prefix: Scalar,
        nested: frozenset[str],
        field_name: str,
    ) -> Wire | None:
        if (builtin := self._builtin(ann)) is not None:
            return StructRef(builtin)
        if isinstance(ann, griffe.ExprSubscript):
            repeat = self._repeat_parts(ann, field_name)
            if repeat is not None:
                elem_ann, count = repeat
                inner = self._base_wire(elem_ann, type_kw, prefix, nested, field_name)
                if inner is None:
                    return None
                return Repeat(inner, prefix if count is None else None, count)
            mapping = self._map_parts(ann, field_name)
            if mapping is not None:
                key = self._base_wire(mapping[0], type_kw, prefix, nested, field_name)
                value = self._base_wire(mapping[1], type_kw, prefix, nested, field_name)
                if key is None or value is None:
                    return None
                return Map(key, value, prefix)
            return None
        if not isinstance(ann, griffe.ExprName):
            return None
        name = ann.name
        if name in nested or name in self._enum_names:
            scalar = self._enum_wire(type_kw, field_name)
            if scalar is None and name in nested:
                raise CompilerError(
                    f"{field_name}: a nested enum cannot be string-coded "
                    f"(field(type=str)) -- use an integer wire primitive, or lift "
                    f"the enum to module scope"
                )
            return EnumRef(name, scalar)
        if name in self._struct_names:
            return StructRef(name)
        if name in ("str", "bytes"):
            return Str()
        if name in PRIMITIVES:
            return Scalar(name, varint=name in VARINT_PRIMITIVES)
        if name in self._alias_primitive:
            target = self._alias_primitive[name]
            return Scalar(target, varint=target in VARINT_PRIMITIVES)
        return None

    @staticmethod
    def _enum_wire(type_kw: str | None, field_name: str) -> Scalar | None:
        """Resolve `field(type=...)` for an enum field. `str` is name-coded
        (returns None); any other primitive is the integer wire."""
        if type_kw is None:
            raise CompilerError(
                f"{field_name}: enum-typed field requires field(type=<primitive>) "
                f"-- e.g. type=uvarint32 or type=str"
            )
        if type_kw == "str":
            return None
        if type_kw not in PRIMITIVES:
            raise CompilerError(
                f"{field_name}: unknown wire primitive {type_kw!r}; "
                f"valid: {sorted(PRIMITIVES)}"
            )
        return Scalar(type_kw, varint=type_kw in VARINT_PRIMITIVES)

    def _with_endian(self, base: Wire, endian: str | None, field_name: str) -> Wire:
        if endian is None:
            return base
        big = endian == "big"
        if isinstance(base, Scalar):
            return replace(base, big_endian=big)
        if isinstance(base, EnumRef) and base.scalar is not None and not base.scalar.varint:
            return replace(base, scalar=replace(base.scalar, big_endian=big))
        raise CompilerError(self._endian_scope_error(field_name))

    @staticmethod
    def _endian_scope_error(field_name: str) -> str:
        return (
            f"{field_name}: field(endian=...) only applies to fixed-width "
            f"primitive or fixed-width integer-coded enum fields"
        )

    # --- when= predicates ----------------------------------------------------

    def _predicate(
        self,
        lam: _Ann,
        field_name: str,
        nested: frozenset[str],
        earlier: frozenset[str],
    ) -> Pred:
        """Lower a `field(when=lambda p: ...)` lambda into a `Pred` tree."""
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
    ) -> Pred:
        def child(n: griffe.Expr | str) -> Pred:
            return self._pred_node(n, param, field_name, nested, earlier)

        if isinstance(node, griffe.ExprBoolOp):
            return Pred(node.operator, operands=tuple(child(v) for v in node.values))
        if isinstance(node, griffe.ExprUnaryOp) and node.operator == "not":
            return Pred("not", operands=(child(node.value),))
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
            return Pred(op, operands=(child(node.left), child(node.comparators[0])))
        if isinstance(node, griffe.ExprAttribute):
            return self._pred_attr(node, param, field_name, nested, earlier)
        literal = self._as_int(node)
        if literal is not None:
            return Pred("int", text=str(literal))
        raise CompilerError(
            f"{field_name}: field(when=...) contains an unsupported expression: "
            f"{node}"
        )

    def _pred_attr(
        self,
        node: griffe.ExprAttribute,
        param: str,
        field_name: str,
        nested: frozenset[str],
        earlier: frozenset[str],
    ) -> Pred:
        """`param.field` is a `field` leaf, `Enum.MEMBER` an `enum` leaf."""
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
            return Pred("field", text=tail)
        if head in nested or head in self._enum_names:
            return Pred("enum", text=f"{head}.{tail}")
        raise CompilerError(
            f"{field_name}: field(when=...) reference {head!r} is neither the "
            f"lambda parameter nor a known enum"
        )

    # --- griffe Expr helpers -------------------------------------------------

    @staticmethod
    def _is_none(arm: object) -> bool:
        return arm == "None"

    def _builtin(self, ann: _Ann) -> str | None:
        """The name of the compiler built-in `ann` refers to, or None. A
        built-in is named bare -- a `@builtin`-decorated type like `CompoundTag`,
        or `UUID` from `from uuid import UUID` -- or as the stdlib `uuid.UUID`."""
        if isinstance(ann, griffe.ExprName):
            if ann.name in self._builtins or ann.name == "UUID":
                return ann.name
            return None
        if isinstance(ann, griffe.ExprAttribute) and str(ann) == "uuid.UUID":
            return "UUID"
        return None

    @staticmethod
    def _flatten_union(ann: _Ann) -> list[griffe.Expr | str] | None:
        """Flatten a `A | B | ...` annotation into its arms in source order,
        or None when `ann` is not a `|` expression."""
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

    @staticmethod
    def _is_int_enum(cls: griffe.Class) -> bool:
        return any(
            isinstance(b, griffe.ExprName) and b.name == "IntEnum" for b in cls.bases
        )

    @staticmethod
    def _is_builtin(cls: griffe.Class) -> bool:
        """Whether `cls` carries the bare `@builtin` decorator -- a type the
        compiler references but never defines, trusting a hand-written codec."""
        return any(
            isinstance(dec.value, griffe.ExprName) and dec.value.name == "builtin"
            for dec in cls.decorators
        )

    @staticmethod
    def _as_int(value: object) -> int | None:
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _call_arg(expr: _Ann, fn_name: str, kw: str) -> _Ann:
        """The value expression of `fn_name(..., kw=<value>)`, else None."""
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

    def _int_kwarg(self, expr: _Ann, fn_name: str, kw: str) -> int | None:
        value = self._call_arg(expr, fn_name, kw)
        return self._as_int(value) if value is not None else None

    def _name_kwarg(self, expr: _Ann, fn_name: str, kw: str) -> str | None:
        value = self._call_arg(expr, fn_name, kw)
        return value.name if isinstance(value, griffe.ExprName) else None

    def _str_kwarg(self, expr: _Ann, fn_name: str, kw: str) -> str | None:
        value = self._call_arg(expr, fn_name, kw)
        if isinstance(value, str) and len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
            return value[1:-1]
        return None

    def _class_since(self, cls: griffe.Class) -> int | None:
        for dec in cls.decorators:
            since = self._int_kwarg(dec.value, "type", "since")
            if since is not None:
                return since
        return None

    def _class_until(self, cls: griffe.Class) -> int | None:
        for dec in cls.decorators:
            until = self._int_kwarg(dec.value, "type", "until")
            if until is not None:
                return until
        return None

    def _packet_id(self, cls: griffe.Class) -> int | None:
        for dec in cls.decorators:
            pid = self._int_kwarg(dec.value, "packet", "id")
            if pid is not None:
                return pid
        return None

    def _packet_since(self, cls: griffe.Class) -> int | None:
        for dec in cls.decorators:
            since = self._int_kwarg(dec.value, "packet", "since")
            if since is not None:
                return since
        return None

    def _member_value(self, value: _Ann) -> tuple[int, int | None, int | None] | None:
        """Parse `0` or `value(N, since=V, until=U)` into (value, since, until)."""
        direct = self._as_int(value)
        if direct is not None:
            return direct, None, None
        if not (
            isinstance(value, griffe.ExprCall)
            and isinstance(value.function, griffe.ExprName)
            and value.function.name == "value"
            and value.arguments
        ):
            return None
        ivalue = self._as_int(value.arguments[0])
        if ivalue is None:
            return None
        return (
            ivalue,
            self._int_kwarg(value, "value", "since"),
            self._int_kwarg(value, "value", "until"),
        )
