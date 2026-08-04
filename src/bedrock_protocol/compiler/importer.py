"""Import driving + file access — protoc analog of `compiler/importer.{h,cc}`.

protoc keeps three jobs apart: a `SourceTree` opens files by name, a `Parser` turns
one file's syntax into a `FileDescriptorProto`, and an `Importer` decides which
files to open and drives the other two. This module holds the first and third.

The DSL has no `import` statement of its own, so `Importer` reads Python's: it
follows `from X.Y import ...` between modules, and additionally pulls in each
input's owning package (where `__version__` lives), which a schema file does not
necessarily name.
"""

from __future__ import annotations

import ast
import copy
from pathlib import Path
from typing import cast

import griffe

from bedrock_protocol.descriptor import (
    PRIMITIVES,
    CompilerError,
    FileSet,
    PrimitiveAlias,
    PrimitiveType,
    TypeAlias,
)

from .parser import Parser, SymbolTable, enum_underlying_of, is_enum, nested_declarations


class _DeclarationCollector(griffe.Extension):
    """Every `class` statement, in source order, grouped by module, plus the
    `with field(when=...)` blocks griffe cannot model.

    griffe keeps members in a dict, so a type declared twice to model a wire
    reshape survives only as its last declaration -- silently. `on_class_members`
    fires per `ClassDef` once its body is attached, before that overwrite, so both
    shapes reach the parser."""

    def __init__(self) -> None:
        self.by_module: dict[str, list[griffe.Class]] = {}

    def on_class_node(self, *, node: object, agent: object, **kwargs: object) -> None:
        """Hoist each `with field(when=...)` block's fields into the class body,
        merging the block's predicate into every field as `_group_when=` and the
        block's index as `_group_id=`. griffe has no `with` in its object model,
        so the block has to be flattened before the body is visited; the index is
        what keeps the hoisted fields identifiable as one block afterwards."""
        if not isinstance(node, ast.ClassDef):
            return
        body: list[ast.stmt] = []
        group = 0
        for stmt in node.body:
            guard = _with_guard(stmt, node.name)
            if guard is None:
                body.append(stmt)
                continue
            block, predicate = guard
            for inner in block.body:
                _merge_guard(inner, predicate, group)
                body.append(inner)
            group += 1
        node.body = body

    def on_class_members(self, *, node: object, cls: griffe.Class, agent: object, **kwargs: object) -> None:
        parent = cls.parent
        if isinstance(parent, griffe.Module):
            self.by_module.setdefault(parent.path, []).append(cls)


def _with_guard(stmt: ast.stmt, owner: str) -> tuple[ast.With, ast.expr] | None:
    """A `with field(when=...):` block paired with its predicate, or None.

    A guard block takes exactly `when=`. Anything else has to be an error: an
    unrecognised keyword would leave the block unhoisted, and its fields would
    reach the wire ungated without a word said."""
    if not isinstance(stmt, ast.With) or len(stmt.items) != 1:
        return None
    ctx = stmt.items[0].context_expr
    if not (isinstance(ctx, ast.Call) and isinstance(ctx.func, ast.Name) and ctx.func.id == "field"):
        return None
    predicate: ast.expr | None = None
    for kw in ctx.keywords:
        if kw.arg == "when":
            predicate = kw.value
        else:
            raise CompilerError(f"{owner}: a with field(...) guard block takes no {kw.arg!r} keyword, only when=")
    if predicate is None or ctx.args:
        raise CompilerError(f"{owner}: a with field(...) guard block takes exactly field(when=<lambda>)")
    return stmt, predicate


def _merge_guard(stmt: ast.stmt, predicate: ast.expr, group: int) -> None:
    """Merge a block's guard into one hoisted field as `field(_group_when=,
    _group_id=)`. A field with no `field(...)` call gains one; anything that is
    not an annotated assignment is left alone."""
    if not isinstance(stmt, ast.AnnAssign):
        return
    keywords = [
        ast.keyword(arg="_group_when", value=copy.deepcopy(predicate)),
        ast.keyword(arg="_group_id", value=ast.Constant(value=group)),
    ]
    if stmt.value is None:
        stmt.value = ast.Call(func=ast.Name(id="field", ctx=ast.Load()), args=[], keywords=keywords)
    elif isinstance(stmt.value, ast.Call):
        stmt.value.keywords.extend(keywords)
    else:
        return
    ast.copy_location(stmt.value, stmt)
    ast.fix_missing_locations(stmt)


class SourceTree:
    """Opens DSL modules by name — protoc's `SourceTree` / `DiskSourceTree`.

    File access only: it maps a dotted module name onto a file under one of the
    `import_paths` (protoc's `--proto_path`) and hands back griffe's parse of it.
    What the modules mean is the `Parser`'s business; which of them to load is the
    `Importer`'s."""

    def __init__(self, import_paths: list[Path]) -> None:
        self._import_paths = [p.resolve() for p in import_paths]
        self._declarations: dict[str, list[griffe.Class]] = {}

    @property
    def import_paths(self) -> list[Path]:
        """The roots a module name is resolved against — protoc's `--proto_path`."""
        return self._import_paths

    def open(self, name: str, root: Path) -> griffe.Module:
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

    def declarations_of(self, module_name: str) -> list[list[griffe.Class]]:
        """The module's classes grouped by name, each group in source order. A
        group of more than one is a version-redeclared type."""
        groups: dict[str, list[griffe.Class]] = {}
        for cls in self._declarations.get(module_name, []):
            if cls.is_alias:
                continue
            groups.setdefault(cls.name, []).append(cls)
        return list(groups.values())

    def module_name_and_root(self, path: Path) -> tuple[str, Path]:
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


class Importer:
    """Loads a schema and everything it reaches — protoc's `Importer`.

    Owns the cross-file symbol table: unlike protoc, whose parser records a type
    reference as a name string for `DescriptorBuilder` to resolve later, ours
    resolves references while parsing, so every module must be loaded and
    classified before any is parsed.
    """

    def __init__(self, source_tree: SourceTree) -> None:
        self._source_tree = source_tree

    def load_all(self, sources: tuple[Path, ...]) -> FileSet:
        """Load every source file plus its transitive imports, returning the
        complete `FileSet`. The order in `sources` is preserved in `outputs`."""
        griffe_modules: dict[str, griffe.Module] = {}
        stems: dict[str, str] = {}
        output_names: list[str] = []
        for src in sources:
            name, root = self._source_tree.module_name_and_root(src)
            griffe_modules[name] = self._source_tree.open(name, root)
            stems[name] = src.stem
            output_names.append(name)
        self._load_owning_packages(griffe_modules, output_names)
        self._follow_imports(griffe_modules, output_names)
        symbols = self._classify(griffe_modules)
        parser = Parser(symbols)
        files = {
            name: parser.parse_file(
                name,
                mod,
                stems.get(name, name),
                set(griffe_modules),
                self._imports_of(mod),
                self._source_tree.declarations_of(name),
            )
            for name, mod in griffe_modules.items()
        }
        return FileSet(
            files=files,
            outputs=tuple(output_names),
            version=_dsl_version(griffe_modules),
        )

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
                for ip in self._source_tree.import_paths:
                    if ip.joinpath(*parts[:cut], "__init__.py").is_file():
                        loaded[parent] = self._source_tree.open(parent, ip)
                        break

    def _follow_imports(self, loaded: dict[str, griffe.Module], seed: list[str]) -> None:
        pending = list(seed)
        while pending:
            for dep in self._imports_of(loaded[pending.pop()]):
                if dep in loaded:
                    continue
                parts = dep.split(".")
                for ip in self._source_tree.import_paths:
                    module = ip.joinpath(*parts).with_suffix(".py")
                    package = ip.joinpath(*parts, "__init__.py")
                    if module.is_file() or package.is_file():
                        loaded[dep] = self._source_tree.open(dep, ip)
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

    def _classify(self, loaded: dict[str, griffe.Module]) -> SymbolTable:
        enum_names: set[str] = set()
        enum_underlying: dict[str, PrimitiveType | None] = {}
        struct_names: set[str] = set()
        aliases_by_name: dict[str, PrimitiveAlias | TypeAlias] = {}
        primitive_aliases_by_module: dict[str, tuple[PrimitiveAlias, ...]] = {}
        type_aliases_by_module: dict[str, tuple[TypeAlias, ...]] = {}

        def register(decls: list[griffe.Class], scope: str) -> None:
            """Record one declared type under its dotted path, then recurse into
            whatever it nests."""
            name = f"{scope}.{decls[0].name}" if scope else decls[0].name
            if is_enum(decls[0]):
                enum_names.add(name)
                enum_underlying[name] = enum_underlying_of(decls[0])
                return
            struct_names.add(name)
            for group in nested_declarations(decls):
                register(group, name)

        for mod_name in loaded:
            for decls in self._source_tree.declarations_of(mod_name):
                register(decls, "")

        # Alias pass — after classification, since an alias may reference any
        # class. Declaration order is the resolution order.
        for name, mod in loaded.items():
            primitives: list[PrimitiveAlias] = []
            others: list[TypeAlias] = []
            parser = Parser(
                SymbolTable(
                    enum_names=frozenset(enum_names),
                    enum_underlying=enum_underlying,
                    struct_names=frozenset(struct_names),
                    aliases_by_name=aliases_by_name,
                )
            )
            for attr_name, attr in list(mod.attributes.items()) + list(mod.type_aliases.items()):
                if attr_name == "package" or attr_name in PRIMITIVES or attr.value is None:
                    continue
                if getattr(attr, "is_alias", False):
                    continue
                alias = parser.parse_alias(attr_name, attr.value)
                if alias is None:
                    continue
                aliases_by_name[alias.name] = alias
                if isinstance(alias, PrimitiveAlias):
                    primitives.append(alias)
                else:
                    others.append(alias)
            primitive_aliases_by_module[name] = tuple(primitives)
            type_aliases_by_module[name] = tuple(others)

        return SymbolTable(
            enum_names=frozenset(enum_names),
            enum_underlying=enum_underlying,
            struct_names=frozenset(struct_names),
            aliases_by_name=aliases_by_name,
            primitive_aliases_by_module=primitive_aliases_by_module,
            type_aliases_by_module=type_aliases_by_module,
        )


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
