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
from typing import cast

import griffe

from bedrock_protocol.descriptor import (
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


@dataclass(frozen=True)
class _ClassifyResult:
    enum_names: frozenset[str]
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
        return cast(
            griffe.Module,
            griffe.load(name, search_paths=[str(root)], allow_inspection=False),
        )

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
        struct_names: set[str] = set()
        aliases_by_name: dict[str, PrimitiveAlias | TypeAlias] = {}
        primitive_aliases_by_module: dict[str, tuple[PrimitiveAlias, ...]] = {}
        type_aliases_by_module: dict[str, tuple[TypeAlias, ...]] = {}

        for mod in loaded.values():
            for cls in mod.classes.values():
                if cls.is_alias:
                    continue
                (enum_names if _is_int_enum(cls) else struct_names).add(cls.name)

        # Alias pass — after classification, since an alias may reference any
        # class. Declaration order is the resolution order.
        for name, mod in loaded.items():
            primitives: list[PrimitiveAlias] = []
            others: list[TypeAlias] = []
            ctx = _AnnotationContext(frozenset(enum_names), frozenset(struct_names), aliases_by_name)
            for attr_name, attr in list(mod.attributes.items()) + list(mod.type_aliases.items()):
                if attr_name == "package" or attr_name in PRIMITIVES or attr.value is None:
                    continue
                if getattr(attr, "is_alias", False):
                    continue
                alias = ctx.parse_alias(attr_name, attr.value)
                if alias is None:
                    continue
                aliases_by_name[alias.name] = alias
                (primitives if isinstance(alias, PrimitiveAlias) else others).append(alias)
            primitive_aliases_by_module[name] = tuple(primitives)
            type_aliases_by_module[name] = tuple(others)

        return _ClassifyResult(
            enum_names=frozenset(enum_names),
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
        ctx = _AnnotationContext(classified.enum_names, classified.struct_names, classified.aliases_by_name)
        enums: list[Enum] = []
        structs: list[Struct] = []
        order: list[str] = []
        for cls in mod.classes.values():
            if cls.is_alias:
                continue
            if _is_int_enum(cls):
                e = ctx.enum(cls)
                enums.append(e)
                order.append(e.name)
            else:
                s = ctx.struct(cls)
                structs.append(s)
                order.append(s.name)
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
        for name, attr in cls.attributes.items():
            if attr.value is None:
                continue
            number = _as_int(attr.value)
            if number is None:
                continue
            values.append(EnumValue(name, number))
        return Enum(cls.name, tuple(values))

    def struct(self, cls: griffe.Class) -> Struct:
        fields = tuple(self.field(attr) for attr in cls.attributes.values())
        since = _decorator_int(cls, "packet", "since")
        if since is None:
            since = _decorator_int(cls, "type", "since")
        return Struct(
            name=cls.name,
            fields=fields,
            packet_id=_decorator_int(cls, "packet", "id"),
            since=since,
            until=_decorator_int(cls, "packet", "until"),
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
        if not isinstance(ann, griffe.ExprName):
            return None
        name = ann.name
        if name in self.enum_names:
            return EnumType(name, _enum_scalar(type_kw, field_name))
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


def _is_int_enum(cls: griffe.Class) -> bool:
    return any(isinstance(b, griffe.ExprName) and b.name in ("IntEnum", "IntFlag") for b in cls.bases)


def _is_none(case: object) -> bool:
    """A literal `None` in source. griffe spells a keyword literal as the bare
    string `'None'` (vs `ExprName('Other')` for a name reference)."""
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


def _list_element(ann: griffe.ExprSubscript, field_name: str) -> griffe.Expr | str | None:
    """The element annotation of a `list[T]` subscript, or None for anything else."""
    if isinstance(ann.left, griffe.ExprName) and ann.left.name == "list":
        return ann.slice
    return None


def _enum_scalar(type_kw: str | None, field_name: str) -> PrimitiveType | None:
    if type_kw is None:
        raise CompilerError(
            f"{field_name}: enum-typed field requires field(type=<primitive>) -- e.g. type=uvarint32 or type=str"
        )
    if type_kw == "str":
        return None
    if type_kw not in PRIMITIVES:
        raise CompilerError(f"{field_name}: unknown wire primitive {type_kw!r}; valid: {sorted(PRIMITIVES)}")
    return PrimitiveType(name=type_kw)


def _repeat_prefix(call: _Ann, field_name: str) -> PrimitiveType:
    name = _name_kwarg(call, "field", "prefix")
    if name is None:
        return PrimitiveType(name="uvarint32")
    if name not in PRIMITIVES:
        raise CompilerError(f"{field_name}: field(prefix=...) must be an integer primitive, got {name!r}")
    return PrimitiveType(name=name)


def _call_arg(expr: _Ann, fn_name: str, kw: str) -> _Ann:
    if not (
        isinstance(expr, griffe.ExprCall) and isinstance(expr.function, griffe.ExprName) and expr.function.name == fn_name
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
