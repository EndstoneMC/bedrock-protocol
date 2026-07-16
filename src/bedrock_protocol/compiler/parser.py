"""Frontend — `.py` DSL files to `File` instances.

Analog of protoc's `io::Tokenizer` + `compiler::Parser` + `importer`. We use
griffe to statically parse the user's Python source: the DSL decorators
(`@packet`, `@type`, `field()`) are runtime no-ops, so griffe never executes
them, only reads them as AST.

A `SourceTree` follows `from X.Y import ...` between modules so a struct in one
file can reference a type declared in another. Files passed to `load_all()`
are listed as `outputs` so the CLI knows which to emit.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, cast

import griffe

from bedrock_protocol.descriptor import (
    BUILTIN_ANNOTATIONS,
    PRIMITIVES,
    CompilerError,
    Enum,
    EnumType,
    EnumValue,
    Field,
    FieldType,
    FieldVersion,
    File,
    FileSet,
    OptionalType,
    PrimitiveAlias,
    PrimitiveType,
    RepeatedType,
    Struct,
    StructType,
    TypeAlias,
    VariantType,
)

_Ann = griffe.Expr | str | None


class _DeclarationCollector(griffe.Extension):
    """Every `class` statement, in source order, grouped by module.

    griffe keeps members in a dict, so a type declared twice to model a wire
    reshape survives only as its last declaration -- silently. This hook fires per
    `ClassDef` once its body is attached, before that overwrite, so both shapes
    reach the parser."""

    def __init__(self) -> None:
        self.by_module: dict[str, list[griffe.Class]] = {}

    def on_class_members(self, *, node: object, cls: griffe.Class, agent: object, **kwargs: object) -> None:
        parent = cls.parent
        if isinstance(parent, griffe.Module):
            self.by_module.setdefault(parent.path, []).append(cls)


@dataclass(frozen=True)
class _ClassifyResult:
    enum_names: frozenset[str]
    enum_underlying: dict[str, PrimitiveType | None]
    struct_names: frozenset[str]
    aliases_by_name: dict[str, PrimitiveAlias | TypeAlias]
    primitive_aliases_by_module: dict[str, tuple[PrimitiveAlias, ...]]
    type_aliases_by_module: dict[str, tuple[TypeAlias, ...]]


class SourceTree:
    """Loads `.py` DSL files via griffe, lowers them to `File`.

    `import_paths` are the roots the loader uses to resolve `from X.Y import
    ...` between modules — protoc's `--proto_path` equivalent."""

    def __init__(self, import_paths: list[Path]) -> None:
        self._import_paths = [p.resolve() for p in import_paths]
        self._declarations: dict[str, list[griffe.Class]] = {}

    # --- public API ---------------------------------------------------------

    def load_all(self, sources: tuple[Path, ...]) -> FileSet:
        """Load every source file plus its transitive imports, returning the
        complete `FileSet`. The order in `sources` is preserved in `outputs`."""
        griffe_modules: dict[str, griffe.Module] = {}
        stems: dict[str, str] = {}
        output_names: list[str] = []
        for src in sources:
            name, root = self._module_name_and_root(src)
            griffe_modules[name] = self._griffe_load(name, root)
            stems[name] = src.stem
            output_names.append(name)
        self._load_owning_packages(griffe_modules, output_names)
        self._load_version_module(griffe_modules, output_names)
        self._follow_imports(griffe_modules, output_names)
        classified = self._classify(griffe_modules)
        files = {
            name: self._lower_file(name, mod, stems.get(name, name), griffe_modules, classified)
            for name, mod in griffe_modules.items()
        }
        return FileSet(
            files=files,
            outputs=tuple(output_names),
            version=_dsl_version(griffe_modules),
        )

    # --- griffe loading -----------------------------------------------------

    def _griffe_load(self, name: str, root: Path) -> griffe.Module:
        collector = _DeclarationCollector()
        module = cast(
            griffe.Module,
            griffe.load(
                name,
                search_paths=[str(root)],
                allow_inspection=False,
                extensions=griffe.Extensions(collector),
            ),
        )
        # A load may reach modules a previous one already covered; replace rather
        # than append so a module's declarations are never counted twice.
        self._declarations.update(collector.by_module)
        return module

    def _declarations_of(self, module_name: str) -> list[list[griffe.Class]]:
        """The module's classes grouped by name, each group in source order. A
        group of more than one is a version-redeclared type."""
        groups: dict[str, list[griffe.Class]] = {}
        for cls in self._declarations.get(module_name, []):
            if cls.is_alias:
                continue
            groups.setdefault(cls.name, []).append(cls)
        return list(groups.values())

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

    def _load_owning_packages(self, loaded: dict[str, griffe.Module], seed: list[str]) -> None:
        """Load each input's parent package(s) so the DSL surface module is
        available even when the input has no `from <package> import ...` line
        (it is where `__version__` lives)."""
        for name in seed:
            parts = name.split(".")
            for cut in range(len(parts) - 1, 0, -1):
                parent = ".".join(parts[:cut])
                if parent in loaded:
                    continue
                for ip in self._import_paths:
                    if ip.joinpath(*parts[:cut], "__init__.py").is_file():
                        loaded[parent] = self._griffe_load(parent, ip)
                        break

    def _load_version_module(self, loaded: dict[str, griffe.Module], seed: list[str]) -> None:
        """Always load the DSL's `version` submodule (which declares the
        compiler-owned `ProtocolVersion` enum) so any file with versioned types
        can spell the typed `_<ProtocolVersion V>` selector without importing
        it. The enum stays DSL-owned; the import is just no longer boilerplate."""
        for name in seed:
            parts = name.split(".")
            for cut in range(len(parts) - 1, 0, -1):
                mod_name = ".".join(parts[:cut] + ["version"])
                if mod_name in loaded:
                    break
                for ip in self._import_paths:
                    if ip.joinpath(*parts[:cut], "version.py").is_file():
                        loaded[mod_name] = self._griffe_load(mod_name, ip)
                        break
                else:
                    continue
                break

    def _follow_imports(self, loaded: dict[str, griffe.Module], seed: list[str]) -> None:
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
        """Source modules `mod`'s `from X.Y import ...` lines refer to. Names
        with a `_`-prefixed component (the DSL surface itself) are omitted."""
        out: set[str] = set()
        for member in mod.members.values():
            target = getattr(member, "target_path", None)
            if target is None or "." not in str(target):
                continue
            dep = str(target).rsplit(".", 1)[0]
            if not any(part.startswith("_") for part in dep.split(".")):
                out.add(dep)
        return out

    # --- classification -----------------------------------------------------

    def _classify(self, loaded: dict[str, griffe.Module]) -> _ClassifyResult:
        enum_names: set[str] = set()
        enum_underlying: dict[str, PrimitiveType | None] = {}
        struct_names: set[str] = set()
        aliases_by_name: dict[str, PrimitiveAlias | TypeAlias] = {}
        primitive_aliases_by_module: dict[str, tuple[PrimitiveAlias, ...]] = {}
        type_aliases_by_module: dict[str, tuple[TypeAlias, ...]] = {}

        for mod_name in loaded:
            for decls in self._declarations_of(mod_name):
                cls = decls[0]
                if _is_int_enum(cls):
                    enum_names.add(cls.name)
                    enum_underlying[cls.name] = _enum_underlying(cls)
                else:
                    struct_names.add(cls.name)

        # Alias pass — after classification, since an alias may reference any
        # class. Declaration order is the resolution order.
        for name, mod in loaded.items():
            primitives: list[PrimitiveAlias] = []
            others: list[TypeAlias] = []
            ctx = _AnnotationContext(frozenset(enum_names), enum_underlying, frozenset(struct_names), aliases_by_name)
            for attr_name, attr in list(mod.attributes.items()) + list(mod.type_aliases.items()):
                if attr_name == "package" or attr_name in PRIMITIVES or attr.value is None:
                    continue
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
            enum_underlying=enum_underlying,
            struct_names=frozenset(struct_names),
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
            classified.enum_names,
            classified.enum_underlying,
            classified.struct_names,
            classified.aliases_by_name,
        )
        enums: list[Enum] = []
        structs: list[Struct] = []
        order: list[str] = []
        for decls in self._declarations_of(name):
            if _is_int_enum(decls[0]):
                if len(decls) > 1:
                    raise CompilerError(
                        f"{decls[0].name}: an enum cannot be redeclared; version-gate its members with value(since=)"
                    )
                e = ctx.enum(decls[0])
                enums.append(e)
                order.append(e.name)
            else:
                st = ctx.struct(decls)
                structs.append(st)
                order.append(st.name)
        imports = tuple(sorted(d for d in self._imports_of(mod) if d in loaded and d != name))
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


# --- annotation lowering ------------------------------------------------------


@dataclass(frozen=True)
class _AnnotationContext:
    """The name dictionaries the annotation walker reads."""

    enum_names: frozenset[str]
    enum_underlying: dict[str, PrimitiveType | None]
    struct_names: frozenset[str]
    aliases: dict[str, PrimitiveAlias | TypeAlias]

    # ---- aliases -----------------------------------------------------------

    def parse_alias(self, name: str, value: griffe.Expr | str) -> PrimitiveAlias | TypeAlias | None:
        if isinstance(value, griffe.ExprName) and value.name in PRIMITIVES:
            return PrimitiveAlias(name, value.name)
        target = self.type(name, value, None)
        return None if target is None else TypeAlias(name, target)

    # ---- declarations ------------------------------------------------------

    def enum(self, cls: griffe.Class) -> Enum:
        values: list[EnumValue] = []
        previous: int | None = None
        for name, attr in cls.attributes.items():
            if attr.value is None:
                continue
            number = _enum_number(cls.name, name, attr.value, previous)
            values.append(EnumValue(name, number))
            previous = number
        return Enum(cls.name, tuple(values), _enum_underlying(cls))

    def struct(self, decls: list[griffe.Class]) -> Struct:
        """One struct from every declaration of its name. A type redeclared over
        adjacent ranges models a wire reshape: each declaration's fields carry that
        declaration's range, so a snapshot narrows to exactly one shape -- including
        its field *order*, which a reshaped packet may change."""
        _check_redeclaration(decls)
        fields: list[Field] = []
        for decl in decls:
            lo, hi = _decl_since(decl), _decl_until(decl)
            for attr in decl.attributes.values():
                (version,) = self.field(attr).versions
                narrowed = FieldVersion(
                    type=version.type,
                    since=_tighten(version.since, lo, max),
                    until=_tighten(version.until, hi, min),
                )
                fields.append(Field(attr.name, (narrowed,)))
        return Struct(
            name=decls[0].name,
            fields=tuple(fields),
            packet_id=_decorator_int(decls[0], "packet", "id"),
            since=_decl_since(decls[0]),
            until=_decl_until(decls[-1]),
            builtin=any(_has_decorator(d, "builtin") for d in decls),
        )

    def field(self, attr: griffe.Attribute) -> Field:
        call = attr.value
        t = self.type(attr.name, attr.annotation, call)
        version = FieldVersion(
            type=t,
            since=_int_kwarg(call, "field", "since"),
            until=_int_kwarg(call, "field", "until"),
        )
        return Field(attr.name, (version,))

    # ---- enum wire type ----------------------------------------------------

    def _enum_scalar(self, type_kw: str | None, field_name: str, enum_name: str) -> PrimitiveType | None:
        """The wire encoding of an enum-typed field: `field(type=)` if given
        (`str` marks it name-coded), else derived from the enum's underlying type."""
        if type_kw == "str":
            return None
        if type_kw is not None:
            if type_kw not in PRIMITIVES:
                raise CompilerError(f"{field_name}: unknown wire primitive {type_kw!r}; valid: {sorted(PRIMITIVES)}")
            return PrimitiveType(name=type_kw)
        underlying = self.enum_underlying.get(enum_name)
        if underlying is None:
            raise CompilerError(
                f"{field_name}: {enum_name} declares no underlying type, so its wire encoding "
                f"cannot be derived -- give the enum one as a second base "
                f"(class {enum_name}(IntEnum, uint8)) or pass field(type=...)"
            )
        return _default_enum_wire(underlying)

    # ---- field-type walker -------------------------------------------------

    def type(self, field_name: str, ann: _Ann, call: _Ann) -> FieldType | None:
        type_kw = _name_kwarg(call, "field", "type")
        prefix = _repeat_prefix(call, field_name)
        cases = _flatten_union(ann)
        if cases is not None:
            return self._union_type(cases, field_name, type_kw, prefix)
        return self._base_type(ann, type_kw, prefix, field_name)

    def _union_type(
        self,
        cases: list[griffe.Expr | str],
        field_name: str,
        type_kw: str | None,
        prefix: PrimitiveType,
    ) -> FieldType | None:
        if len(cases) == 2 and sum(_is_none(a) for a in cases) == 1:
            inner_ann = next(a for a in cases if not _is_none(a))
            base = self._base_type(inner_ann, type_kw, prefix, field_name)
            return None if base is None else OptionalType(base)
        types: list[FieldType | None] = []
        for case in cases:
            if _is_none(case):
                types.append(None)
                continue
            t = self._base_type(case, type_kw, prefix, field_name)
            if t is None:
                return None
            types.append(t)
        return VariantType(tuple(types))

    def _base_type(
        self,
        ann: _Ann,
        type_kw: str | None,
        prefix: PrimitiveType,
        field_name: str,
    ) -> FieldType | None:
        if isinstance(ann, griffe.ExprSubscript):
            elem = _list_element(ann, field_name)
            if elem is None:
                return None
            inner = self._base_type(elem, type_kw, prefix, field_name)
            return None if inner is None else RepeatedType(inner=inner, prefix=prefix)
        cases = _flatten_union(ann)
        if cases is not None:
            return self._union_type(cases, field_name, type_kw, prefix)
        dotted = _dotted_name(ann)
        if dotted is not None and dotted in BUILTIN_ANNOTATIONS:
            return StructType(BUILTIN_ANNOTATIONS[dotted])
        if not isinstance(ann, griffe.ExprName):
            return None
        name = ann.name
        if name in self.enum_names:
            return EnumType(name, self._enum_scalar(type_kw, field_name, name))
        if name in self.struct_names:
            return StructType(name)
        if name in PRIMITIVES:
            return PrimitiveType(name=name)
        alias = self.aliases.get(name)
        if isinstance(alias, PrimitiveAlias):
            return PrimitiveType(name=alias.primitive, alias=alias.name)
        if isinstance(alias, TypeAlias):
            return alias.target
        return None


# --- module-free helpers ------------------------------------------------------


def _package_of(mod: griffe.Module) -> str | None:
    attr = mod.attributes.get("package")
    if attr is None or attr.value is None:
        return None
    return str(attr.value).strip("'\"")


def _dsl_version(loaded: dict[str, griffe.Module]) -> int | None:
    """Pull `__version__` off any loaded module that declares it -- in practice
    the DSL surface module (`protocol/__init__.py`). The single source for the
    protocol version this project targets; the CLI raises if it is missing."""
    for mod in loaded.values():
        attr = mod.attributes.get("__version__")
        if attr is None or attr.value is None:
            continue
        try:
            return int(str(attr.value))
        except ValueError:
            continue
    return None


def _base_name(base: griffe.Expr | str) -> str | None:
    """Last component of a base-class expression. Both the bare `IntEnum` and
    the dotted `enum.IntEnum` spelling yield "IntEnum"."""
    if isinstance(base, griffe.ExprAttribute):
        base = base.values[-1]
    return base.name if isinstance(base, griffe.ExprName) else None


def _is_int_enum(cls: griffe.Class) -> bool:
    return any(_base_name(b) in ("IntEnum", "IntFlag") for b in cls.bases)


#: DSL fixed-width integer primitive -> (size in bytes, signed). The set an enum
#: may declare as its C++ underlying type; a varint is an encoding, not a type.
_INT_WIDTHS: dict[str, tuple[int, bool]] = {
    "int8": (1, True),
    "uint8": (1, False),
    "int16": (2, True),
    "uint16": (2, False),
    "int": (4, True),
    "int32": (4, True),
    "uint32": (4, False),
    "int64": (8, True),
    "uint64": (8, False),
}


def _default_enum_wire(underlying: PrimitiveType) -> PrimitiveType:
    """The default wire encoding: underlying type, enum-as-value and compression.
    One byte has nothing to compress and goes as-is; wider compresses to
    `[u]varint32`, or `[u]varint64` at eight, signedness following the underlying."""
    size, signed = _INT_WIDTHS[underlying.name]
    if size == 1:
        return underlying
    width = 64 if size == 8 else 32
    return PrimitiveType(name=f"{'' if signed else 'u'}varint{width}")


def _enum_underlying(cls: griffe.Class) -> PrimitiveType | None:
    """The enum's C++ underlying type, written as a second base
    (`class MemoryCategory(IntEnum, uint8)`). None means the C++ default, `int`."""
    for base in cls.bases:
        name = _base_name(base)
        if name is None or name in ("IntEnum", "IntFlag"):
            continue
        if name not in _INT_WIDTHS:
            raise CompilerError(
                f"{cls.name}: enum underlying type must be a fixed-width integer primitive, got {name!r}; "
                f"valid: {sorted(_INT_WIDTHS)}"
            )
        return PrimitiveType(name=name)
    return None


def _is_none(case: object) -> bool:
    """A literal `None` in source. griffe spells a keyword literal as the bare
    string `'None'` (vs `ExprName('Other')` for a name reference)."""
    return case == "None"


def _dotted_name(ann: _Ann) -> str | None:
    """`uuid.UUID` as the string "uuid.UUID"; None for anything not a dotted path."""
    if not isinstance(ann, griffe.ExprAttribute):
        return None
    parts = [v.name for v in ann.values if isinstance(v, griffe.ExprName)]
    return ".".join(parts) if len(parts) == len(ann.values) else None


def _has_decorator(cls: griffe.Class, name: str) -> bool:
    """A bare decorator like `@builtin`, which carries no call parentheses."""
    return any(_base_name(d.value) == name for d in cls.decorators)


def _decl_since(cls: griffe.Class) -> int | None:
    since = _decorator_int(cls, "packet", "since")
    return since if since is not None else _decorator_int(cls, "type", "since")


def _decl_until(cls: griffe.Class) -> int | None:
    until = _decorator_int(cls, "packet", "until")
    return until if until is not None else _decorator_int(cls, "type", "until")


def _tighten(own: int | None, decl: int | None, pick: Callable[[int, int], int]) -> int | None:
    """A field's bound against its declaration's: the narrower of the two wins, so
    `field(since=486)` inside an `until=1001` declaration spans [486, 1001)."""
    if own is None:
        return decl
    if decl is None:
        return own
    return pick(own, decl)


def _check_redeclaration(decls: list[griffe.Class]) -> None:
    """Redeclarations must tile one range: same id, each `until` meeting the next
    `since`, and only the last left open. Anything else silently drops or
    double-counts a shape at some snapshot."""
    if len(decls) == 1:
        return
    name = decls[0].name
    ids = {_decorator_int(d, "packet", "id") for d in decls}
    if len(ids) > 1:
        raise CompilerError(f"{name}: every redeclaration must share one packet id, got {sorted(map(str, ids))}")
    for current, following in zip(decls, decls[1:]):
        until, since = _decl_until(current), _decl_since(following)
        if until is None:
            raise CompilerError(f"{name}: only the last declaration may omit until=; an earlier one leaves it open")
        if until != since:
            raise CompilerError(
                f"{name}: redeclarations must be adjacent -- until={until} is followed by since={since}"
            )


def _enum_number(enum_name: str, name: str, value: griffe.Expr | str, previous: int | None) -> int:
    """A member's wire number: an int literal, or `auto()` for previous + 1."""
    if isinstance(value, griffe.ExprCall) and _base_name(value.function) == "auto":
        return 0 if previous is None else previous + 1
    number = _as_int(value)
    if number is None:
        raise CompilerError(f"{enum_name}.{name}: enum member must be an int literal or auto(), got {value!r}")
    return number


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


def _list_element(ann: griffe.ExprSubscript, field_name: str) -> griffe.Expr | str | None:
    """The element annotation of a `list[T]` subscript, or None for anything else."""
    if isinstance(ann.left, griffe.ExprName) and ann.left.name == "list":
        return ann.slice
    return None


def _repeat_prefix(call: _Ann, field_name: str) -> PrimitiveType:
    name = _name_kwarg(call, "field", "prefix")
    if name is None:
        return PrimitiveType(name="uvarint32")
    if name not in PRIMITIVES:
        raise CompilerError(f"{field_name}: field(prefix=...) must be an integer primitive, got {name!r}")
    return PrimitiveType(name=name)


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


def _decorator_int(cls: griffe.Class, decorator: str, kwarg: str) -> int | None:
    for dec in cls.decorators:
        v = _int_kwarg(dec.value, decorator, kwarg)
        if v is not None:
            return v
    return None
